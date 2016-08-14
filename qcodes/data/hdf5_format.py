import numpy as np
import h5py
import re
import math
import os

from .data_array import DataArray
from .format import Formatter

"""
list for things that are still missing
* dataset has no way of including units
* there is an assumption that data arrays are preallocated in the dataset.
  this breaks down when measurements are interupted before they terminate
  and/or when doing adaptive measurements where you do not know beforehand
  how many datapoints you will get.
* Add more robust way of incremental write (check if all arrays are ready
  to increment)

"""


class HDF5Format(Formatter):
    """
    HDF5 formatter for saving qcodes datasets
    """
    def __init__(self):
        """
        Instantiates the datafile using the location provided by the io_manager
        see h5py detailed info
        """
        self.data_object = None

    def _create_file(self, filepath):
        folder, _filename = os.path.split(filepath)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        data_object = h5py.File(filepath, 'a')
        return data_object

    def read(self, data_set):
        """
        Tested that it correctly opens a file, needs a better way to
        find the actual file. This is not part of the formatter at this point
        """
        location = data_set.location
        filepath = location
        self.data_object = h5py.File(filepath, 'r+')
        for i, array_id in enumerate(
                self.data_object['Data Arrays'].keys()):
            # Decoding string is needed because of h5py/issues/379
            name = array_id  # will be overwritten if not in file
            dat_arr = self.data_object['Data Arrays'][array_id]
            if 'label' in dat_arr.attrs.keys():
                label = dat_arr.attrs['label'].decode()
            else:
                label = None
            if 'name' in dat_arr.attrs.keys():
                name = dat_arr.attrs['name'].decode()
            if 'units' in dat_arr.attrs.keys():
                units = dat_arr.attrs['units'].decode()
            else:
                units = None
            is_setpoint = str_to_bool(dat_arr.attrs['is_setpoint'].decode())
            if not is_setpoint:
                set_arrays = dat_arr.attrs['set_arrays']
                set_arrays = [s.decode() for s in set_arrays]
            else:
                set_arrays = ()

            d_array = DataArray(
                name=name, array_id=array_id, label=label, parameter=None,
                units=units,
                is_setpoint=is_setpoint, set_arrays=(),
                preset_data=dat_arr.value[:, 0])
            data_set.add_array(d_array)
            # needed because I cannot add them at this point
            data_set.arrays[array_id]._sa_array_ids = set_arrays

        # Add copy/ref of setarrays (not array id only)
        # Note, this is not pretty but a result of how the dataset works
        for array_id, d_array in data_set.arrays.items():
            print(d_array._sa_array_ids)
            for sa_id in d_array._sa_array_ids:
                d_array.set_arrays += (data_set.arrays[sa_id], )

    def write(self, data_set, force_write=False):
        """
        """
        if self.data_object is None or force_write:
            # Create the file if it is not there yet
            io_manager = data_set.io
            location = data_set.location
            filename = os.path.split(location)[-1]
            self.filepath = io_manager.join(location +
                                            '/{}.hdf5'.format(filename))
            # note that this creates an hdf5 file in a folder with the same
            # name. This is useful for saving e.g. images in the same folder
            # I think this is a sane default (MAR).
            self.data_object = self._create_file(self.filepath)

        if 'Data Arrays' not in self.data_object.keys():
            self.arr_group = self.data_object.create_group('Data Arrays')
        for array_id in data_set.arrays.keys():
            if array_id not in self.arr_group.keys() or force_write:
                self._create_dataarray_dset(array=data_set.arrays[array_id],
                                            group=self.arr_group)
            dset = self.arr_group[array_id]
            # Resize the dataset and add the new values

            # dataset refers to the hdf5 dataset here
            datasetshape = dset.shape
            old_dlen = datasetshape[0]
            x = data_set.arrays[array_id]
            new_dlen = len(x[~np.isnan(x)])
            new_datasetshape = (new_dlen,
                                datasetshape[1])
            dset.resize(new_datasetshape)
            dset[old_dlen:new_dlen] = \
                data_set.arrays[array_id][old_dlen:new_dlen].reshape(
                    new_datasetshape)

    def _create_dataarray_dset(self, array, group):
        '''
        input arguments
        array:  Dataset data array
        group:  group in the hdf5 file where the dset will be created

        creates a hdf5 datasaset that represents the data array.
        '''
        # Check for empty meta attributes, use array_id if name and/or label
        # is not specified
        if array.label is not None:
            label = array.label
        else:
            label = array.array_id
        if array.name is not None:
            name = array.name
        else:
            name = array.array_id
        if array.units is None:
            array.units = ['']  # used for shape determination
        units = array.units
        # Create the hdf5 dataset
        dset = group.create_dataset(
            array.array_id, (0, len(array.units)),
            maxshape=(None, len(array.units)))
        dset.attrs['label'] = _encode_to_utf8(str(label))
        dset.attrs['name'] = _encode_to_utf8(str(name))
        dset.attrs['units'] = _encode_to_utf8(str(units))
        dset.attrs['is_setpoint'] = _encode_to_utf8(str(array.is_setpoint))

        if not array.is_setpoint:
            set_arrays = []
            for i in range(len(array.set_arrays)):
                set_arrays += [_encode_to_utf8(
                    str(array.set_arrays[i].array_id))]
            dset.attrs['set_arrays'] = set_arrays

        return dset

    def _create_data_arrays_grp(self, arrays):
        self.data_arrays_grp = self.data_object.create_group('Data Arrays')
        # Allows reshaping but does not allow adding extra parameters
        self.dset = self.data_arrays_grp.create_dataset(
            'Data', (0, len(arrays.keys())),
            maxshape=(None, len(arrays.keys())))
        self.dset.attrs['column names'] = _encode_to_utf8(arrays.keys())

        labels= []
        names = []
        units = []
        for key in arrays.keys():
            arr = arrays[key]
            if hasattr(arr, 'label'):
                labels += [arr.label]
            else:
                labels += [key]
            if hasattr(arr, 'name'):
                names += [arr.name]
            else:
                labels += [key]
            if hasattr(arr, 'units'):
                units += [arr.units]
            else:
                units += ['']

        # _encode_to_utf8(str(...)) ensures None gets encoded for h5py aswell
        self.dset.attrs['labels'] = _encode_to_utf8(str(labels))
        self.dset.attrs['names'] = _encode_to_utf8(str(names))
        self.dset.attrs['units'] = _encode_to_utf8(str(units))

        # Added to tell analysis how to extract the data
        self.data_arrays_grp.attrs['datasaving_format'] = _encode_to_utf8(
            'QCodes hdf5 v0.1')

    def write_metadata(self, data_set, io_manager, location, read_first=True):
        print('Write meta data is passing')

    def save_instrument_snapshot(self, snapshot, *args):
        """
        uses QCodes station snapshot to save the last known value of any
        parameter. Only saves the value and not the update time (which is
        known in the snapshot)

        META DATA GROUP
        """
        # Todo: merge with write metadata
        # TODO:  should be pretty easy to add this but am waiting
        # for the metadata of @Merlinsmiles
        set_grp = data_object.create_group('Meta-data')
        inslist = dict_to_ordered_tuples(self.station.instruments)
        for (iname, ins) in inslist:
            instrument_grp = set_grp.create_group(iname)
            par_snap = ins.snapshot()['parameters']
            parameter_list = dict_to_ordered_tuples(par_snap)
            for (p_name, p) in parameter_list:
                try:
                    val = str(p['value'])
                except KeyError:
                    val = ''
                instrument_grp.attrs[p_name] = str(val)


def _encode_to_utf8(s):
    """
    Required because h5py does not support python3 strings
    """
    # converts byte type to string because of h5py datasaving
    if type(s) == str:
        s = s.encode('utf-8')
    # If it is an array of value decodes individual entries
    elif type(s) == np.ndarray or list:
        s = [s.encode('utf-8') for s in s]
    return s


def str_to_bool(s):
    if s == 'True':
        return True
    elif s == 'False':
        return False
    else:
        raise ValueError("Cannot covert {} to a bool".format(s))

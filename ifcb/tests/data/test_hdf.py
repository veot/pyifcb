import os
import unittest

import numpy as np
import h5py as h5
from pandas.testing import assert_frame_equal

from ifcb.tests.utils import withfile, test_dir

from ifcb.data.h5utils import hdf2pd, hdfopen
from ifcb.data.adc import AdcFile
from ifcb.data.roi import RoiFile
from ifcb.data.hdr import parse_hdr_file
from ifcb.data.hdf import roi2hdf, hdr2hdf, adc2hdf, fileset2hdf, hdf2fileset, HdfBin, filesetbin2hdf, bin2hdf
from ifcb.data.files import FilesetBin

from .fileset_info import list_test_filesets, list_test_bins
from .bins import assert_bin_equals

def test_adc_roundtrip(adc, path, group=None):
    with hdfopen(path, group) as h:
        csv = hdf2pd(h)
        assert h.attrs['schema'] == adc.schema._name
    assert_frame_equal(csv, adc.csv)

def test_hdr_roundtrip(hdr, path, group=None):
    with hdfopen(path, group) as h:
        for k,v in hdr.items():
            assert np.all(h.attrs[k] == hdr[k])

def test_roi_roundtrip(roi, path, group=None):
    with hdfopen(path, group) as h:
        index = h.attrs['index']
        assert np.all(index == roi.keys())
        for roi_number in index:
            assert np.all(roi[roi_number] == h[str(roi_number)])
        for roi_number in index:
            assert np.all(roi[roi_number] == h[h['images'][roi_number]])
    
class TestAdcHdf(unittest.TestCase):
    @withfile
    def test_roundtrip(self, path):
        for fs in list_test_filesets():
            adc = AdcFile(fs.adc_path)
            adc2hdf(adc, path, replace=True)
            test_adc_roundtrip(adc, path)

class TestRoiHdf(unittest.TestCase):
    @withfile
    def test_roundtrip(self, path):
        for fs in list_test_filesets():
            with RoiFile(fs.adc_path, fs.roi_path) as roi:
                roi2hdf(roi, path)
                test_roi_roundtrip(roi, path)

class TestHdrHdf(unittest.TestCase):
    @withfile
    def test_roundtrip(self, path):
        for fs in list_test_filesets():
            hdr = parse_hdr_file(fs.hdr_path)
            hdr2hdf(hdr, path)
            test_hdr_roundtrip(hdr, path)

class TestFilesetHdf(unittest.TestCase):
    @withfile
    def test_roundtrip(self, path):
        for fs in list_test_filesets():
            with FilesetBin(fs) as fs_bin:
                filesetbin2hdf(fs_bin, path)
                test_adc_roundtrip(fs_bin.adc_file, path, 'adc')
                test_hdr_roundtrip(fs_bin.hdr_attributes, path, 'hdr')
                test_roi_roundtrip(fs_bin.roi_file, path, 'roi')
                # now test other aspects
                with h5.File(path) as h:
                    assert h.attrs['pid'] == str(fs_bin.pid)
                    assert h.attrs['lid'] == fs_bin.lid
                    assert h.attrs['timestamp'] == fs_bin.timestamp.isoformat()
    @unittest.skip('slow')
    @withfile
    def test_archive(self, path):
        for fs in list_test_filesets():
            fileset2hdf(fs, path, archive=True)
            with h5.File(path) as h:
                archived_adc_data = bytearray(h['archive/adc'])
                with open(fs.adc_path,'rb') as adc_in:
                    adc_data = bytearray(adc_in.read())
                assert np.all(adc_data == archived_adc_data)
                archived_hdr_data = bytearray(h['archive/hdr'])
                with open(fs.hdr_path,'rb') as hdr_in:
                    hdr_data = bytearray(hdr_in.read())
                assert np.all(hdr_data == archived_hdr_data)
                with open(fs.roi_path,'rb') as roi_in:
                    roi_data = bytearray(roi_in.read())
                # now test unarchiving API
                with test_dir() as d:
                    fs_path = os.path.join(d, fs.lid)
                    hdf2fileset(h, fs_path)
                    with open(fs_path + '.adc','rb') as adc_in:
                        unarchived_adc_data = bytearray(adc_in.read())
                    assert np.all(adc_data == unarchived_adc_data)
                    with open(fs_path + '.hdr','rb') as hdr_in:
                        unarchived_hdr_data = bytearray(hdr_in.read())
                    assert np.all(hdr_data == unarchived_hdr_data)
                    with open(fs_path + '.roi','rb') as roi_in:
                        unarchived_roi_data = bytearray(roi_in.read())
                    assert np.all(roi_data == unarchived_roi_data)

class TestHdfBin(unittest.TestCase):
    @withfile
    def test_roundtrip(self, path):
        for fs in list_test_filesets():
            with FilesetBin(fs) as out_bin:
                bin2hdf(out_bin, path)
                with HdfBin(path) as in_bin:
                    assert_bin_equals(in_bin, out_bin)
    @withfile
    def test_multiple_open_group(self, path):
        with hdfopen(path, replace=True) as h:
            for out_bin in list_test_bins():
                out_bin.to_hdf(h, group=out_bin.lid)
                with HdfBin(h, out_bin.lid) as in_bin:
                    assert_bin_equals(in_bin, out_bin)
    @withfile
    def test_multiple_closed_group(self, path):
        with hdfopen(path, replace=True) as h:
            for out_bin in list_test_bins():
                out_bin.to_hdf(h, group=out_bin.lid)
        for out_bin in list_test_bins():
            with HdfBin(path, out_bin.lid) as in_bin:
                assert_bin_equals(in_bin, out_bin)

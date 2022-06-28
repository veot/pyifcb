import unittest
import os
import sys

import numpy as np

from ifcb.data import files
from .fileset_info import TEST_FILES, data_dir, WHITELIST, list_test_filesets, list_test_bins

class TestListUtils(unittest.TestCase):
    def setUp(self):
        self.data_dir = data_dir()
    def test_list_data_dirs(self):
        for dd in files.list_data_dirs(self.data_dir):
            assert 'adc' in [f[-3:] for f in os.listdir(dd)]
    def test_list_data_dirs_prune(self):
        for dd in files.list_data_dirs(self.data_dir):
            for n in os.listdir(dd):
                assert 'decoy.adc' not in n
    def test_list_data_dirs_no_prune(self):
        for dd in files.list_data_dirs(self.data_dir, prune=False):
            for n in os.listdir(dd):
                if 'decoy.adc' in n:
                    return
        raise ValueError('decoy not found with prune=False')
    def test_list_filesets(self):
        """test with validation off and search"""
        paths = list(files.list_filesets(self.data_dir, whitelist=WHITELIST, validate=False))
        assert len(paths) == 5

class TestDataDirectory(unittest.TestCase):
    def setUp(self):
        self.data_dir = data_dir()
        self.default = files.DataDirectory(self.data_dir)
        self.whitelist = files.DataDirectory(self.data_dir, whitelist=WHITELIST)
        self.blacklist = files.DataDirectory(self.data_dir, blacklist=['skip','invalid','empty'])
    def test_iteration(self):
        fss = list(self.default)
        assert len(fss) == 1 # only one whitelisted by default
        fss = list(self.whitelist)
        assert len(fss) == 2 # including whitelisted one
    def test_exists(self):
        fss = [b.fileset for b in self.whitelist]
        for fs in fss:
            assert fs.exists()
            assert os.path.exists(fs.adc_path)
            assert os.path.exists(fs.hdr_path)
            assert os.path.exists(fs.roi_path)
    def test_lids(self):
        fss = [b.fileset for b in self.whitelist]
        lids = [fs.lid for fs in fss]
        for lid in TEST_FILES:
            assert lid in lids
        for fs in fss:
            assert self.whitelist[fs.lid].lid == fs.lid
    @unittest.skip('possible Windows-specific issue')
    def test_getsizes(self):
        for fs in list_test_filesets():
            sizes = TEST_FILES[fs.lid]['sizes']
            assert fs.getsizes() == sizes
            assert fs.getsize() == sum(sizes.values())
    def test_descendants(self):
        assert len(list(self.default.list_descendants())) == 4
        assert len(list(self.blacklist.list_descendants())) == 2

class TestFilesetBin(unittest.TestCase):
    def _bins(self):
        for b in list_test_bins():
            yield b, TEST_FILES[b.lid]
    def test_len(self):
        for b, d in self._bins():
            assert len(b) == d['n_targets'], 'wrong number of targets'
    def test_image_index(self):
        for b, d in self._bins():
            assert len(b.images) == d['n_rois'], 'wrong number of ROIs'
            assert set(b.images) == set(d['roi_numbers']), 'wrong ROI numbers'
    def test_shape(self):
        for b, d in self._bins():
            roi_number = d['roi_number']
            roi_shape = d['roi_shape']
            with b:
                assert b.images[roi_number].shape == roi_shape, 'wrong ROI shape'
    def test_image(self):
        for b, d in self._bins():
            roi_number = d['roi_number']
            roi_slice = d['roi_slice']
            c = d['roi_slice_coords']
            with b:
                assert np.all(b.images[roi_number][tuple(c)] == roi_slice), 'wrong image data'
    def test_bin_open_state(self):
        for b, d in self._bins():
            assert not b.isopen(), 'FilesetBin should start closed'
            b[d['roi_number']] # this will open and close the bin
            assert not b.isopen(), 'after reading single image, FilesetBin should be closed'
            with b:
                assert b.isopen(), 'context mgr on should open bin on enter'
            assert not b.isopen(), 'context mgr should close bin on exit'

class TestEmptyBin(unittest.TestCase):
    def setUp(self):
        dd = files.DataDirectory(data_dir(), whitelist=['empty'])
        self.bins = list(dd)
    def test_len(self):
        for b in self.bins:
            assert len(b) == 0, 'expected empty bin'
    def test_adc_len(self):
        for b in self.bins:
            assert len(b.adc) == 0, 'expected empty adc data'
            assert len(b.adc.columns) > 0, 'expected empty columnar adc data'
    def test_images_adc(self):
        for b in self.bins:
            assert len(b.images_adc) == 0, 'expected empty image adc data'
            assert len(b.images_adc.columns) > 0, 'expected empty columnar image adc data'
    def test_images(self):
        for b in self.bins:
            assert len(b.images) == 0, 'expected no image data'
            for im in b.images:
                assert False, 'expected no image data'
    def test_headers(self):
        for b in self.bins:
            assert len(b.headers) > 0, 'expected headers'
    def test_keys(self):
        for b in self.bins:
            assert len(list(b.keys())) == 0, 'expected no keys in empty bin'
            for k in b:
                assert False, 'expected no keys in empty bin'

class TestImagesAdc(unittest.TestCase):
    def test_images_adc(self):
        for b in list_test_bins():
            d = TEST_FILES[b.lid]
            ia = b.images_adc
            roi_numbers = d['roi_numbers']
            assert np.all(ia.index == roi_numbers)
            
class TestFilesetFragmentBin(TestFilesetBin):
    def _bins(self):
        for b in list_test_bins():
            d = TEST_FILES[b.lid]
            yield b.as_single(d['roi_number']), d
    def test_open_state(self):
        for b in list_test_bins():
            d = TEST_FILES[b.lid]
            s = b.as_single(d['roi_number'])
            assert not b.isopen(), 'bin should not be open'
    def test_open_fail(self):
        for b in list_test_bins():
            d = TEST_FILES[b.lid]
            with b.images as images: # this will close bin on exit
                assert b.isopen(), 'bin is not open'
                with self.assertRaises(ValueError):
                    # this should fail because bin is open
                    b.as_single(d['roi_number'])
    def test_len(self):
        for b, d in self._bins():
            assert len(b) == 2, 'fragment too long'
    def test_image_index(self):
        # pass this test, which would fail because superclass
        # test expects the image index to be complete
        pass

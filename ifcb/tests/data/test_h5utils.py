import unittest
import os
from contextlib import contextmanager

import numpy as np
import h5py as h5
import pandas as pd

from pandas.testing import assert_frame_equal

from ifcb.tests.utils import withfile

from ifcb.data.h5utils import hdfopen, clear_h5_group, pd2hdf, hdf2pd

class TestH5Utils(unittest.TestCase):
    @withfile
    def test_hdfopen(self, F):
        attr = 'test'
        v1, v2 = 5, 6
        for group in [None, 'g']:
            with hdfopen(F, group, replace=True) as f:
                f.attrs[attr] = v1
            assert os.path.exists(F), 'failed to create HDF file'
            with hdfopen(F, group) as f:
                assert f.attrs[attr] == v1, 'attribute value wrong'
            with hdfopen(F, group, replace=True) as f:
                f.attrs[attr] = v2
            with hdfopen(F, group) as f:
                assert f.attrs[attr] == v2, 'replacing attribute failed'
    @withfile
    def test_clear_h5_group(self, F):
        with h5.File(F, 'w') as f:
            f['foo/bar'] = [1,2,3]
            f.attrs['baz'] = 5
        with h5.File(F, 'a') as f:
            assert 'foo' in f.keys(), 'missing key'
            assert 'baz' in f.attrs.keys(), 'missing attribute'
            clear_h5_group(f)
        with h5.File(F) as f:
            assert not f.keys(), 'failed to clear group'
            assert not f.attrs.keys(), 'failed to clear attributes'
    @withfile
    def test_df_h5_roundtrip(self, F):
        r = np.random.RandomState(0) # seed
        data = r.normal(size=(5,3))
        in_df = pd.DataFrame(data=data)
        @contextmanager
        def roundtrip(): # test dataframe roundtrip
            if os.path.exists(F):
                os.remove(F)
            with hdfopen(F,replace=True) as g:
                yield in_df
                pd2hdf(g, in_df)
                out_df = hdf2pd(g)
                assert_frame_equal(in_df, out_df, check_index_type='equiv', check_column_type='equiv')
        with roundtrip():
            in_df.index = r.permutation(in_df.index)
        with roundtrip():
            in_df.columns = ['col%d' % n for n in range(len(in_df.columns))]
        with roundtrip():
            in_df['new_col'] = np.arange(len(in_df)) # different type column
        with roundtrip():
            in_df.index.name = 'hello'

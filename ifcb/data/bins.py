"""
Bin API. Provides consistent access to IFCB raw data stored
in various formats.
"""
from functools import lru_cache

from .adc import SCHEMA
from .hdr import TEMPERATURE, HUMIDITY

from .utils import BaseDictlike

from ..metrics.ml_analyzed import compute_ml_analyzed

class BaseBin(BaseDictlike):
    """
    Base class for Bin implementations. Providing common features.

    The bin PID is available as a Pid object via the "pid" property.
    Subclasses must implement this.

    Bins are dict-like. Keys are target numbers, values are ADC records.
    ADC records are tuples.

    Also supports an "adc" property that is a Pandas DataFrame containing
    ADC data. Subclasses are required to provide this. The default dictlike
    implementation uses that property.

    Context manager support is provided for implementations
    that must open files or other data streams.
    """
    @property
    def lid(self):
        """
        :returns str: the bin's LID.
        """
        return self.pid.bin_lid
    @property
    @lru_cache()
    def images_adc(self):
        """
        :returns pandas.DataFrame: the ADC data, minus targets that
          are not associated with images
        """
        return self.adc[self.adc[self.schema.ROI_WIDTH] > 0]
    @property
    def timestamp(self):
        """
        :returns datetime: the bin's timestamp.
        """
        return self.pid.timestamp
    @property
    def schema(self):
        return SCHEMA[self.pid.schema_version]
    # context manager default implementation
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    # dictlike interface
    def keys(self):
        yield from self.adc.index
    def has_key(self, k):
        return k in self.adc.index
    def __len__(self):
        return len(self.adc.index)
    def get_target(self, target_number):
        """
        Retrieve a target record by target number

        :param target_number: the target number
        """
        d = tuple(self.adc[c][target_number] for c in self.adc.columns)
        return d
    def __getitem__(self, target_number):
        return self.get_target(target_number)
    # metrics
    @lru_cache()
    def _get_ml_analyzed(self):
        return compute_ml_analyzed(self)
    @property
    def ml_analyzed(self):
        ma, _, _ = self._get_ml_analyzed()
        return ma
    @property
    def look_time(self):
        _, lt, _ = self._get_ml_analyzed()
        return lt
    @property
    def run_time(self):
        _, _, rt = self._get_ml_analyzed()
        return rt
    @property
    def inhibit_time(self):
        return self.run_time - self.look_time
    @property
    def n_triggers(self):
        try:
            last_row = self.adc.iloc[-1]
        except IndexError: # empty ADC file
            return 0
        return int(last_row[self.schema.TRIGGER])
    @property
    def trigger_rate(self):
        """return trigger rate in triggers / s"""
        return 1.0 * self.n_triggers / self.run_time
    @property
    def temperature(self):
        return self.header(TEMPERATURE)
    @property
    def humidity(self):
        return self.header(HUMIDITY)
    # convenience APIs for writing in different formats
    def read(self):
        with self:
            new_bin = BaseBin()
            new_bin.pid = self.pid.copy()
            new_bin.headers = self.headers.copy()
            new_bin.adc = self.adc
            new_bin.images = { k:v for k,v in self.images.items() }
            return new_bin
    def to_hdf(self, hdf_file, group=None, replace=True):
        from .hdf import bin2hdf
        bin2hdf(self, hdf_file, group=group, replace=replace)
    def to_zip(self, zip_path):
        from .zip import bin2zip
        bin2zip(self, zip_path)
    def to_mat(self, mat_path):
        from .matlab import bin2mat
        bin2mat(self, mat_path)

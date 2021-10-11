from abc import abstractmethod, ABC


class DataObject(ABC):
    @classmethod
    def from_database(cls):
        raise NotImplementedError()

    @classmethod
    def from_cache(cls):
        raise NotImplementedError()

    def save_data(self):
        raise NotImplementedError()

    @staticmethod
    def get_filepath(outdir: str) -> str:
        raise NotImplementedError()
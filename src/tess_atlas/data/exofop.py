import logging
import os
from typing import List

import pandas as pd
from tess_atlas.utils import NOTEBOOK_LOGGER_NAME
from tess_atlas.data.data_utils import get_file_timestamp
import lightkurve as lk
import functools
from tqdm.auto import tqdm

logger = logging.getLogger(NOTEBOOK_LOGGER_NAME)

EXOFOP = "https://exofop.ipac.caltech.edu/tess/"
TIC_DATASOURCE = EXOFOP + "download_toi.php?sort=toi&output=csv"
TIC_SEARCH = EXOFOP + "target.php?id={tic_id}"

DIR = os.path.dirname(__file__)


@functools.lru_cache()
def get_tic_database(clean=False):
    # if we have a cached database file
    cached_file = os.path.join(DIR, "cached_tic_database.csv")
    if os.path.isfile(cached_file) and not clean:
        cache_time = get_file_timestamp(cached_file)
        logger.debug(f"Loading cached TIC list (last modified {cache_time})")
        return pd.read_csv(cached_file)

    # go online to grab database and cache
    db = pd.read_csv(TIC_DATASOURCE)
    db[["TOI int", "planet count"]] = (
        db["TOI"].astype(str).str.split(".", 1, expand=True)
    )
    db = db.astype({"TOI int": "int", "planet count": "int"})
    db["Multiplanet System"] = db["TOI int"].duplicated(keep=False)
    db["Single Transit"] = db["Period (days)"] <= 0
    db["Lightcurve Availible"] = [  # slow!!
        is_lightcurve_availible(tic)
        for tic in tqdm(db["TIC ID"], desc="Checking TIC for lightcurve data")
    ]
    db.to_csv(cached_file, index=False)
    return db


def get_tic_id_for_toi(toi_number: int) -> int:
    tic_db = get_tic_database()
    toi = tic_db[tic_db["TOI"] == toi_number + 0.01].iloc[0]
    return int(toi["TIC ID"])


@functools.lru_cache()
def get_toi_numbers_for_different_categories():
    tic_db = get_tic_database()
    tic_db = filter_db_without_lk(tic_db, remove=True)
    multi = tic_db[tic_db["Multiplanet System"]]
    single = tic_db[tic_db["Single Transit"]]
    norm = tic_db[
        (~tic_db["Single Transit"]) & (~tic_db["Multiplanet System"])
    ]
    dfs = [multi, single, norm]
    toi_dfs = {}
    for df, name in zip(dfs, ["multi", "single", "norm"]):
        toi_ids = list(set(df["TOI"].astype(int)))
        toi_dfs[name] = pd.DataFrame(dict(toi_numbers=toi_ids))
    return toi_dfs


def get_tic_data_from_database(toi_numbers: List[int]) -> pd.DataFrame:
    """Get rows of about a TIC  from ExoFOP associated with a TOI target.
    :param int toi_numbers: The list TOI number for which the TIC data is required
    :return: Dataframe with all TOIs for the TIC which contains TOI {toi_id}
    :rtype: pd.DataFrame
    """
    tic_db = get_tic_database()
    tics = [get_tic_id_for_toi(toi) for toi in toi_numbers]
    dfs = [tic_db[tic_db["TIC ID"] == tic].sort_values("TOI") for tic in tics]
    tois_for_tic = pd.concat(dfs)
    if len(tois_for_tic) < 1:
        raise ValueError(f"TOI data for TICs-{tics} does not exist.")
    return tois_for_tic


def get_tic_url(tic_id):
    return TIC_SEARCH.format(tic_id=tic_id)


def filter_db_without_lk(db, remove=True):
    if remove:
        db = db[db["Lightcurve Availible"] == True]
    return db


def get_toi_list(remove_toi_without_lk=True):
    db = get_tic_database()
    db = filter_db_without_lk(db, remove_toi_without_lk)
    return list(set(db["TOI"].values.astype(int)))


def is_lightcurve_availible(tic):
    # TODO: would be better if we use
    # tess_atlas.lightcurve_data.search_for_lightkurve_data
    # however -- getting a silly import error -- probably recursive :(
    search = lk.search_lightcurve(
        target=f"TIC {tic}", mission="TESS", author="SPOC"
    )
    if len(search) > 1:
        return True
    return False

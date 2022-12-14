from enum import Enum
from pathlib import Path
from typing import Dict, List, Set, Text, Tuple, Type, Union
from .custom import create_protocol, get_init, get_custom_protocol_class_name
from .database import Database
from .config import get_database_yml
import yaml


class OverrideType(Enum):
    OVERRIDE = 0  # replace existing
    WARN_OVERRIDES = 1  # warn when trying to replace existing
    IGNORE_OVERRIDES = 2  # never replace existing


class Registry:
    """Stores the data from one (or multiple !) database.yml files."""

    def __init__(self) -> None:
        # Mapping of database.yml paths to their config in a dictionary
        self.configs: Dict[Path, Dict] = dict()

        # Content of the "Database" root item (=where to find file content)
        self.sources: Dict[Text, List[Text]] = dict()

        # Mapping of database names to a type that inherits from Database
        self.databases: Dict[Text, Type] = dict()

        # Mapping of tasks name to the set of databases that support this task
        self.tasks: Dict[Text, Set[Text]] = dict()

    def load_databases(
        self,
        *paths: Union[Text, Path],
        allow_override: OverrideType = OverrideType.WARN_OVERRIDES,
    ):
        """Load all database yaml files passed as parameter into this config.

        Parameters
        ----------
        allow_override : OverrideType, optional
            How to treat duplicates protocols between multiple yml files.
            Files will be treated in the order they're passed.
            If overriding, last yml to define a protocol will set it.
            If not, first yml to define a protocol will be set it.
            By default, all override attemps will result in a warning, by default OverrideType.WARN_OVERRIDES
        """

        for path in paths:
            fullpath = get_database_yml(path)  # only expands ~ to full path

            with open(fullpath, "r") as fp:
                config = yaml.load(fp, Loader=yaml.SafeLoader)

            self.configs[fullpath] = config
            self._process_config(fullpath, allow_override=allow_override)

        self._reload_meta_protocols()

    def _process_database(
        self,
        db_name,
        db_entries: dict,
        database_yml: Union[Text, Path] = None,
        allow_override: OverrideType = OverrideType.WARN_OVERRIDES,
    ):
        """Loads all protocols from this database to this Registry.

        Parameters
        ----------
        db_name : _type_
            Name of the database
        db_entries : dict
            Dict of all entries under this database (this should be tasks)
        database_yml : Union[Text, Path], optional
            Path to the database.yml file. Not required for X protocols, by default None
        """

        db_name = str(db_name)

        # maps tuple (task,protocol) to the custom protocol class
        protocols: Dict[Tuple[Text, Text], Type] = dict()

        for task_name, task_entries in db_entries.items():
            for protocol, protocol_entries in task_entries.items():
                protocol = str(protocol)
                CustomProtocol = create_protocol(
                    db_name, task_name, protocol, protocol_entries, database_yml
                )
                if CustomProtocol is None:
                    continue

                protocols[(task_name, protocol)] = CustomProtocol

                # update TASKS dictionary
                if task_name not in self.tasks:
                    self.tasks[task_name] = set()
                self.tasks[task_name].add(db_name)

        # Merge old protocols dict with the new one (according to current override rules)
        if db_name in self.databases:
            for p_id, p in self.databases[db_name]._protocols.items():
                # if this protocol already existed (=conflict/override)
                if p_id in protocols:
                    if allow_override == OverrideType.OVERRIDE:
                        pass  # keep the new value
                    elif allow_override == OverrideType.WARN_OVERRIDES:
                        t_name, p_name = p_id
                        realname = get_custom_protocol_class_name(
                            db_name, t_name, p_name
                        )
                        raise Warning(
                            f"Couldn't override already loaded task {realname}. Allow or ignore overrides to get rid of this message."
                        )
                    elif allow_override == OverrideType.IGNORE_OVERRIDES:
                        protocols[p_id] = p  # put back the old value
                else:
                    protocols[p_id] = p

        # create database class on-the-fly
        protocol_list = [
            (task, p_name, p_type) for (task, p_name), p_type in protocols.items()
        ]
        self.databases[db_name] = type(
            db_name,
            (Database,),
            {"__init__": get_init(protocol_list), "_protocols": protocols},
        )

    def _process_config(
        self,
        database_yml: Union[Text, Path],
        config: dict = None,
        allow_override: OverrideType = OverrideType.WARN_OVERRIDES,
    ):
        """Register all protocols (but meta protocols) and all file sources defined in configuration file.

        Parameters
        ----------
        database_yml : Union[Text, Path]
            Path to the database.yml
        config : dict, optional
            Dictionary containing all data parsed from the database.yml file.
            Loads the config from self.configs if left to None, by default None
        """

        database_yml = Path(database_yml)
        if config is None:
            config = self.configs[database_yml]

        databases = config.get("Protocols", dict())

        # make sure meta-protocols are processed last (relies on the fact that
        # dicts are iterated in insertion order since Python 3.6)
        x = databases.pop("X", None)
        if x is not None:
            databases["X"] = x
            # TODO: add postprocessing reloading X protocol

        for db_name, db_entries in databases.items():
            self._process_database(
                db_name, db_entries, database_yml, allow_override=allow_override
            )

        # process sources
        # TODO: decide how to handle source overriding
        for db_name, value in config.get("Databases", dict()).items():
            if not isinstance(value, list):
                value = [value]

            path_list: List[str] = list()
            for p in value:
                path = Path(p)
                if not path.is_absolute():
                    path = database_yml.parent / path
                path_list.append(str(path))
            self.sources[str(db_name)] = path_list

    def _reload_meta_protocols(self):
        """Reloads all meta protocols from all database.yml files loaded."""

        # TODO: decide how to handle X protocol overriding.

        self.databases.pop("X", None)

        for db_yml, config in self.configs.items():
            databases = config.get("Protocols", dict())
            if "X" in databases:
                self._process_database("X", databases["X"], None)



# registry singleton
registry = Registry()
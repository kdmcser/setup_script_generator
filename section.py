# encoding=gbk
import os
from typing import Dict, Set, List


class FileStruct(object):
    def __init__(self):
        self.base_dir = ""
        self.src_root = ""
        self.dest_root = ""
        self.overwrite = None
        self.need_uninstall = True
        self.dir_file_map = dict()
        self.files = list()
        self.dirs = list()

    @staticmethod
    def create(base_dir: str, src_root: str, dest_root: str, overwrite: str, need_uninstall: bool):
        file_struct = FileStruct()
        file_struct.base_dir = base_dir
        file_struct.src_root = src_root
        file_struct.dest_root = dest_root
        file_struct.do_list(src_root, "")
        file_struct.overwrite = overwrite
        file_struct.need_uninstall = need_uninstall
        return file_struct

    def do_list(self, src_root: str, relative_root: str):
        full_path = os.path.join(self.base_dir, src_root, relative_root) if relative_root else os.path.join(self.base_dir, src_root)
        for file in os.listdir(full_path):
            relative_file = os.path.join(relative_root, file)
            if os.path.isfile(os.path.join(full_path, file)):
                if relative_root not in self.dir_file_map:
                    self.dir_file_map[relative_root] = list()
                self.dir_file_map[relative_root].append(relative_file)
                self.files.append(relative_file)
            else:
                self.do_list(src_root, relative_file)
        self.dirs.append(relative_root)


class Section(object):
    section_index = 0
    group_index = 0

    def __init__(self):
        self.name = ""
        self.cn_name = ""
        self.desc = ""
        self.files = list()
        self.install_types = list()
        self.children = list()

    @classmethod
    def get_name(cls, is_group):
        if is_group:
            cls.group_index += 1
            return "GRP%02d" % cls.group_index
        else:
            cls.section_index += 1
            return "SEC%02d" % cls.section_index

    @staticmethod
    def create(json_obj: Dict[str, list], base_dir: str, install_types: List[str]):
        section = Section()
        section.name = Section.get_name("children" in json_obj)
        section.cn_name = json_obj["name"]
        section.desc = json_obj["desc"]
        if "install_types" in json_obj:
            section.load_install_types(json_obj["install_types"], install_types)

        if "children" in json_obj:
            for child in json_obj["children"]:
                child_section = Section.create(child, base_dir, install_types)
                section.children.append(child_section)
            return section

        files = json_obj["files"]
        for src_root, value in files.items():
            dest_root, overwrite, need_uninstall = Section.parse_file_value(src_root, value)
            src_root = src_root.replace("/", "\\")
            dest_root = dest_root.replace("/", "\\")
            if dest_root == ".":
                dest_root = "$INSTDIR"
            elif not dest_root.startswith("$"):
                dest_root = os.path.join("$INSTDIR", dest_root)
            section.files.append(FileStruct.create(base_dir, src_root, dest_root, overwrite, need_uninstall))
        return section

    def load_install_types(self, install_types: List[str], ref_install_types: List[str]):
        self.install_types.clear()
        if "RO" in install_types:
            self.install_types.append("RO")
            return

        for install_type in install_types:
            if install_type not in ref_install_types:
                raise ValueError("Not found install type [%s]" % install_type)
            else:
                self.install_types.append(ref_install_types.index(install_type) + 1)
        pass

    @staticmethod
    def parse_file_value(src_root: str, value:object):
        if isinstance(value, str):
            dest_root = value
            overwrite = None
            need_uninstall = True
        elif isinstance(value, dict):
            dest_root = value["dest"]
            overwrite = value["overwrite"]
            need_uninstall = value["need_uninstall"]
        else:
            raise ValueError("Unsupported files value type [%s] of [%s]" % (type(value).__name__, src_root))
        return dest_root, overwrite, need_uninstall

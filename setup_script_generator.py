# encoding=utf8
import json
import os
from string import Template
from typing import List, Set

from cmd_generator import CmdGenerator
from section import Section
from config import *


def check_install_dirs(sections: List[Section]):
    install_dirs = set()
    parent_dirs = set()
    for section in sections:
        for fs in section.files:
            cur_dir = os.path.join(fs.base_dir, fs.src_root)
            install_dirs.add(cur_dir)
            while cur_dir != fs.base_dir:
                cur_dir = os.path.dirname(cur_dir)
                parent_dirs.add(cur_dir)
    check_dir(file_dir, "", install_dirs, parent_dirs)


def check_dir(base_root: str, relative_root: str, install_dirs: Set[str], parent_dirs: Set[str]):
    full_dir = os.path.join(base_root, relative_root)
    file_names = os.listdir(full_dir)
    for file_name in file_names:
        full_file_name = os.path.join(full_dir, file_name)
        relative_path = os.path.join(relative_root, file_name)
        if os.path.isdir(full_file_name):
            if full_file_name in install_dirs or full_file_name + "\\" in install_dirs:
                continue
            elif full_file_name in parent_dirs or full_file_name + "\\" in parent_dirs:
                check_dir(base_root, os.path.join(relative_root, file_name), install_dirs, parent_dirs)
            else:
                print("Miss Element [%s]!" % full_file_name)
    pass


if __name__ == "__main__":
    with open(json_file, "r", encoding='utf8') as fp:
        section_objs = json.load(fp)
    with open(install_type_file, "r", encoding='utf8') as fp:
        install_types = json.load(fp)
    sections = list(map(lambda obj: Section.create(obj, file_dir, install_types), section_objs))
    cmd_generator = CmdGenerator(sections, install_types)
    template_map = {
        "__version__": version,
        "__install_types__": cmd_generator.generate_install_type_cmd(),
        "__section_install__": cmd_generator.generate_install_cmd(),
        "__section_desc__": cmd_generator.generate_section_desc(),
        "__uninstall_files__": cmd_generator.generate_uninstall_files_cmd(),
        "__uninstall_dirs__": cmd_generator.generate_uninstall_dirs_cmd()
    }
    check_install_dirs(sections)

    with open(template_file, "r", encoding='utf8') as fp:
        template = Template(fp.read())
    result = template.safe_substitute(template_map)

    with open(output_file, "w", encoding='utf16') as fp:
        fp.write(result)
    pass

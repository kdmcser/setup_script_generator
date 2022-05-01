# encoding=utf8
import json
import os
from string import Template
from typing import List, Set

from cmd_generator import CmdGenerator
from section import Section
from config import *


def get_install_file_and_dir_set(sections: List[Section]):
    dirs = set()
    files = set()
    for section in sections:
        for fs in section.files:
            if not fs.need_uninstall:
                continue
            for dir_name in fs.dirs:
                dirs.add(os.path.join(fs.dest_root, dir_name))
            for file_name in fs.files:
                files.add(os.path.join(fs.dest_root, file_name))
    return dirs, files


def check_dir(base_root: str, relative_root: str, install_dirs: Set[str], install_files: Set[str]):
    full_dir = os.path.join(base_root, relative_root) if relative_root != "." else base_root
    dest_dir = "$INSTDIR" if relative_root == "." else os.path.join("$INSTDIR", relative_root)
    if dest_dir not in install_dirs:
        print(full_dir)
        return
    file_names = os.listdir(full_dir)
    for file_name in file_names:
        if os.path.isdir(file_name):
            check_dir(base_root, os.path.join(relative_root, file_name), install_dirs, install_files)
        else:
            dest_file = os.path.join(dest_dir, file_name)
            if file_name not in install_files:
                print(os.path.join(full_dir, file_name))
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
    install_dirs, install_files = get_install_file_and_dir_set(sections)
    check_dir(file_dir, ".", install_dirs, install_files)

    with open(template_file, "r", encoding='utf8') as fp:
        template = Template(fp.read())
    result = template.safe_substitute(template_map)

    with open(output_file, "w", encoding='utf16') as fp:
        fp.write(result)
    pass

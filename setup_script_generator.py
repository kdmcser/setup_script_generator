# encoding=utf8
import json
from string import Template

from cmd_generator import CmdGenerator
from section import Section
from config import *


if __name__ == "__main__":
    with open(json_file, "r", encoding='UTF-8') as fp:
        section_objs = json.load(fp)
    with open(install_type_file, "r", encoding='UTF-8') as fp:
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
    with open(template_file, "r", encoding='UTF-8') as fp:
        template = Template(fp.read())
    result = template.safe_substitute(template_map)

    with open(output_file, "w") as fp:
        fp.write(result)
    pass

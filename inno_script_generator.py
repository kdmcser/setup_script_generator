# encoding=utf8
import json
import os
from string import Template
from typing import List, Set

from section import Section
from config import *
from setup_script_generator import check_install_dirs


def to_inno_dir(dest_root: str) -> str:
    """把 NSIS 风格的安装目录转换为 Inno Setup 常量。"""
    if dest_root == "$INSTDIR":
        return "{app}"
    if dest_root.startswith("$INSTDIR\\"):
        return "{app}" + dest_root[len("$INSTDIR"):]
    if dest_root.startswith("$DOCUMENTS\\"):
        return "{userdocs}" + dest_root[len("$DOCUMENTS"):]
    return dest_root


# 与 install_type_list.json 顺序一一对应的英文类型名（Inno [Types] 的 Name）
INSTALL_TYPE_NAMES = ["full", "selected", "hota", "sod"]


def type_name(type_index: int) -> str:
    """把 1-based 安装类型索引转换为有意义的英文名。"""
    return INSTALL_TYPE_NAMES[type_index - 1]


class InnoGenerator(object):
    def __init__(self, sections: List[Section], install_types: List[str]):
        self.sections = sections
        self.install_types = install_types
        self.mutex_sections = dict()
        self.parse_mutex_sections()

    def parse_mutex_sections(self):
        for section in self.sections:
            self.parse_mutex_section(section)

    def parse_mutex_section(self, section: Section):
        if section.children:
            for child in section.children:
                self.parse_mutex_section(child)
        elif section.mutex_group is not None:
            self.mutex_sections.setdefault(section.mutex_group, []).append(section)

    @staticmethod
    def component_path(section: Section, parent_path: str) -> str:
        if parent_path:
            return parent_path + "\\" + section.name
        return section.name

    @staticmethod
    def collect_types(section: Section) -> Set[int]:
        """递归收集一个组内所有叶子 section 的安装类型索引。"""
        if section.children:
            result = set()
            for child in section.children:
                result.update(InnoGenerator.collect_types(child))
            return result
        if "RO" in section.install_types:
            return set()
        return set(section.install_types)

    def generate_types(self) -> str:
        cmds = ["[Types]"]
        for i, name in enumerate(self.install_types):
            cmds.append('Name: "%s"; Description: "%s"' % (INSTALL_TYPE_NAMES[i], name))
        cmds.append('Name: "custom"; Description: "自定义安装"; Flags: iscustom')
        return "\n".join(cmds)

    def gen_component(self, section: Section, parent_path: str) -> List[str]:
        lines = list()
        path = self.component_path(section, parent_path)
        if section.children:
            type_names = " ".join(type_name(t) for t in sorted(self.collect_types(section)))
            if type_names:
                lines.append('Name: "%s"; Description: "%s"; Types: %s' % (path, section.cn_name, type_names))
            else:
                lines.append('Name: "%s"; Description: "%s"' % (path, section.cn_name))
            for child in section.children:
                lines.extend(self.gen_component(child, path))
        else:
            parts = ['Name: "%s"; Description: "%s"' % (path, section.cn_name)]
            if "RO" in section.install_types:
                all_types = " ".join(type_name(i + 1) for i in range(len(self.install_types)))
                parts.append("Types: %s custom" % all_types)
                parts.append("Flags: fixed")
            else:
                parts.append("Types: " + " ".join(type_name(t) for t in section.install_types))
                # 互斥组：Inno 用 exclusive 实现同级互斥（NSIS 的 RadioButton 语义）
                if section.mutex_group is not None and len(self.mutex_sections.get(section.mutex_group, [])) > 1:
                    parts.append("Flags: exclusive")
            lines.append("; ".join(parts))
        return lines

    def generate_components(self) -> str:
        cmds = ["[Components]"]
        for section in self.sections:
            cmds.extend(self.gen_component(section, ""))
        return "\n".join(cmds)

    def gen_files(self, section: Section, parent_path: str) -> List[str]:
        lines = list()
        path = self.component_path(section, parent_path)
        if section.children:
            for child in section.children:
                lines.extend(self.gen_files(child, path))
        else:
            for fs in section.files:
                # 跳过空目录：inno 的 "*" 通配符匹配不到文件会编译失败，而 nsis 此时也不复制任何文件
                if not fs.files:
                    continue
                src = os.path.join(fs.base_dir, fs.src_root) + "\\*"
                dest = to_inno_dir(fs.dest_root)
                flags = "recursesubdirs createallsubdirs"
                if fs.overwrite == "off":
                    flags += " onlyifdoesntexist"
                else:
                    flags += " ignoreversion"
                if not fs.need_uninstall:
                    flags += " uninsneveruninstall"
                lines.append(
                    'Source: "%s"; DestDir: "%s"; Flags: %s; Components: %s'
                    % (src, dest, flags, path)
                )
        return lines

    def generate_files(self) -> str:
        cmds = ["[Files]"]
        for section in self.sections:
            cmds.extend(self.gen_files(section, ""))
        return "\n".join(cmds)

    def collect_component_descs(self, section: Section, result: List[str]):
        result.append(section.desc)
        for child in section.children:
            self.collect_component_descs(child, result)

    def generate_component_desc_code(self) -> str:
        """按 [Components] 声明顺序生成组件详细描述数组赋值，对应 NSIS 的 MUI_DESCRIPTION_TEXT。"""
        descs = list()
        for section in self.sections:
            self.collect_component_descs(section, descs)
        lines = ["  SetArrayLength(ComponentDescs, %d);" % len(descs)]
        for i, desc in enumerate(descs):
            lines.append("  ComponentDescs[%d] := '%s';" % (i, desc.replace("'", "''")))
        return "\n".join(lines)


if __name__ == "__main__":
    with open(json_file, "r", encoding='utf8') as fp:
        section_objs = json.load(fp)
    with open(install_type_file, "r", encoding='utf8') as fp:
        install_types = json.load(fp)
    sections = list(map(lambda obj: Section.create(obj, file_dir, install_types), section_objs))
    check_install_dirs(sections)
    generator = InnoGenerator(sections, install_types)
    template_map = {
        "__version__": version,
        "__setup_icon_file__": os.path.join(inno_resource_dir, "vcmi.ico"),
        "__wizard_image_file__": os.path.join(inno_resource_dir, "slide.png"),
        "__wizard_small_image_file__": os.path.join(inno_resource_dir, "small_icon.png"),
        "__language_file__": os.path.join(inno_resource_dir, "ChineseSimplified.isl"),
        "__license_file__": license_file,
        "__types__": generator.generate_types(),
        "__components__": generator.generate_components(),
        "__files__": generator.generate_files(),
        "__component_descs__": generator.generate_component_desc_code(),
    }

    with open(inno_template_file, "r", encoding='utf8') as fp:
        template = Template(fp.read())
    result = template.safe_substitute(template_map)

    with open(inno_output_file, "w", encoding='utf8') as fp:
        fp.write(result)
    print("Generated: %s" % inno_output_file)

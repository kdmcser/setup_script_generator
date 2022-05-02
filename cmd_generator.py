import os.path
from typing import List

from section import Section


class CmdGenerator(object):
    def __init__(self, sections: List[Section], install_types: List[str]):
        self.sections = sections
        self.install_types = install_types

    def generate_install_type_cmd(self):
        cmds = list()
        for install_type in self.install_types:
            cmds.append('InstType "%s"' % install_type)
        return "\n".join(cmds) + "\n"

    @staticmethod
    def generate_section_group_install_cmd(section: Section, tab: int):
        cmds = list()
        cmds.append(' ' * tab + 'SectionGroup "%s" %s' % (section.cn_name, section.name))
        for child in section.children:
            cmds.extend(CmdGenerator.generate_section_install_cmd(child, tab + 2))
            if child != section.children[-1]:
                cmds.append('')
        cmds.append(' ' * tab + 'SectionGroupEnd')
        return cmds

    @staticmethod
    def generate_section_install_cmd(section: Section, tab: int):
        cmds = list()
        cmds.append(' ' * tab + 'Section "%s" %s' % (section.cn_name, section.name))
        if len(section.install_types) == 0:
            pass
        elif "RO" in section.install_types:
            cmds.append(' ' * (tab + 2) + 'SectionIn RO')
        else:
            install_types = list(map(lambda index: str(index), section.install_types))
            cmds.append(' ' * (tab + 2) + 'SectionIn %s' % " ".join(install_types))

        for fs in section.files:
            for dest_dir, files in fs.dir_file_map.items():
                cmds.append(' ' * (tab + 2) + 'SetOutPath "%s"' % os.path.join(fs.dest_root, dest_dir))
                if fs.overwrite is not None:
                    cmds.append(' ' * (tab + 2) + 'SetOverwrite %s' % fs.overwrite)
                for file_name in files:
                    cmds.append(' ' * (tab + 2) + 'File "%s"' % os.path.join(fs.base_dir, fs.src_root, file_name))
        if section.cn_name == "主程序":
            cmds.append(' ' * (tab + 2) + 'CreateDirectory "$SMPROGRAMS\\${PRODUCT_NAME}"')
            cmds.append(' ' * (tab + 2) + 'CreateShortCut "$SMPROGRAMS\\${PRODUCT_NAME}\\地图编辑器.lnk" "$INSTDIR\\vcmieditor.exe"')
            cmds.append(' ' * (tab + 2) + 'CreateShortCut "$SMPROGRAMS\\${PRODUCT_NAME}\\${PRODUCT_NAME}.lnk" "$INSTDIR\\VCMI_launcher.exe"')
            cmds.append(' ' * (tab + 2) + 'CreateShortCut "$DESKTOP\\${PRODUCT_NAME}.lnk" "$INSTDIR\\VCMI_launcher.exe"')
        cmds.append(' ' * tab + 'SectionEnd')
        return cmds

    def generate_install_cmd(self, tab=0):
        cmds = list()
        for section in self.sections:
            if len(section.children) > 0:
                cmds.extend(self.generate_section_group_install_cmd(section, tab))
            else:
                cmds.extend(self.generate_section_install_cmd(section, tab))
            cmds.append('')
        return "\n".join(cmds)

    @staticmethod
    def do_generate_section_desc(section: Section):
        cmds = list()
        cmds.append('  !insertmacro MUI_DESCRIPTION_TEXT ${%s} "%s"' % (section.name, section.desc))
        for child in section.children:
            cmds.extend(CmdGenerator.do_generate_section_desc(child))
        return cmds

    def generate_section_desc(self):
        cmds = list()
        cmds.append('!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN')
        for section in self.sections:
            cmds.extend(self.do_generate_section_desc(section))
        cmds.append('!insertmacro MUI_FUNCTION_DESCRIPTION_END')
        return "\n".join(cmds) + "\n"

    @staticmethod
    def do_generate_uninstall_files_cmd(section: Section):
        cmds = list()
        if len(section.children) > 0:
            for child in section.children:
                cmds.extend(CmdGenerator.do_generate_uninstall_files_cmd(child))
        else:
            for fs in section.files:
                if not fs.need_uninstall:
                    continue
                for file_name in fs.files:
                    cmds.append('  Delete "%s"' % os.path.join(fs.dest_root, file_name))
        return cmds

    def generate_uninstall_files_cmd(self):
        cmds = list()
        for section in self.sections:
            cmds.extend(self.do_generate_uninstall_files_cmd(section))
        return "\n".join(cmds) + "\n"

    @staticmethod
    def get_uninstall_section_dirs(section: Section):
        dirs = list()
        if len(section.children) > 0:
            for child in section.children:
                dirs.extend(CmdGenerator.get_uninstall_section_dirs(child))
        else:
            for fs in section.files:
                if not fs.need_uninstall:
                    continue
                for dir_name in fs.dirs:
                    dirs.append(os.path.join(fs.dest_root, dir_name))
        return dirs

    def generate_uninstall_dirs_cmd(self):
        cmds = list()
        dirs = list()
        for section in self.sections:
            dirs.extend(self.get_uninstall_section_dirs(section))
        for dir_name in sorted(dirs, reverse=True):
            cmds.append('  RMDir "%s"' % dir_name)
        return "\n".join(cmds) + "\n"

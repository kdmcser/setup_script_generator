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

    def generate_install_cmd(self):
        cmds = list()
        for section in self.sections:
            cmds.append('Section "%s" %s' % (section.cn_name, section.name))
            if "RO" in section.install_types:
                cmds.append('  SectionIn RO')
            else:
                install_types = list(map(lambda index: str(index), section.install_types))
                cmds.append('  SectionIn %s' % " ".join(install_types))

            for fs in section.files:
                for dest_dir, files in fs.dir_file_map.items():
                    cmds.append('  SetOutPath "%s"' % os.path.join(fs.dest_root, dest_dir))
                    if fs.overwrite is not None:
                        cmds.append('  SetOverwrite %s' % fs.overwrite)
                    for file_name in files:
                        cmds.append('  File "%s"' % os.path.join(fs.base_dir, fs.src_root, file_name))
            if section.cn_name == "主程序":
                cmds.append('  CreateDirectory "$SMPROGRAMS\\${PRODUCT_NAME}"')
                cmds.append('  CreateShortCut "$SMPROGRAMS\\${PRODUCT_NAME}\\地图编辑器.lnk" "$INSTDIR\\vcmieditor.exe"')
                cmds.append('  CreateShortCut "$SMPROGRAMS\\${PRODUCT_NAME}\\${PRODUCT_NAME}.lnk" "$INSTDIR\\VCMI_launcher.exe"')
                cmds.append('  CreateShortCut "$DESKTOP\\${PRODUCT_NAME}.lnk" "$INSTDIR\\VCMI_launcher.exe"')
            cmds.append('SectionEnd')
        return "\n".join(cmds) + "\n"

    def generate_section_desc(self):
        cmds = list()
        cmds.append('!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN')
        for section in self.sections:
            cmds.append('  !insertmacro MUI_DESCRIPTION_TEXT ${%s} "%s"' % (section.name, section.desc))
        cmds.append('!insertmacro MUI_FUNCTION_DESCRIPTION_END')
        return "\n".join(cmds) + "\n"

    def generate_uninstall_files_cmd(self):
        cmds = list()
        for section in self.sections:
            for fs in section.files:
                if not fs.need_uninstall:
                    continue
                for file_name in fs.files:
                    cmds.append('  Delete "%s"' % os.path.join(fs.dest_root, file_name))
        return "\n".join(cmds) + "\n"

    def generate_uninstall_dirs_cmd(self):
        cmds = list()
        dirs = list()
        for section in self.sections:
            for fs in section.files:
                if not fs.need_uninstall:
                    continue
                for dir_name in fs.dirs:
                    dirs.append(os.path.join(fs.dest_root, dir_name))
        for dir_name in sorted(dirs, reverse=True):
            cmds.append('  RMDir "%s"' % dir_name)
        return "\n".join(cmds) + "\n"

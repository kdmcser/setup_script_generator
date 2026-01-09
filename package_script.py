import os
import zipfile
import shutil
import time
import subprocess


def validate_directory(directory_path):
    """验证目录是否存在且可访问"""
    if not os.path.exists(directory_path):
        print(f"错误: 目录不存在: {directory_path}")
        return False

    if not os.path.isdir(directory_path):
        print(f"错误: 路径不是目录: {directory_path}")
        return False

    return True


def validate_file_access(file_path):
    """验证文件是否可读"""
    if not os.access(file_path, os.R_OK):
        print(f"错误: 文件不可读: {file_path}")
        return False
    return True


def create_content_zip(content_path, zip_path):
    """创建content目录的zip文件"""
    # 检查目标zip文件是否已存在
    if os.path.exists(zip_path):
        print(f"错误: zip文件已存在: {zip_path}")
        return False

    # 验证content目录是否可访问
    if not os.access(content_path, os.R_OK):
        print(f"错误: 目录不可读: {content_path}")
        return False

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_STORED) as zip_file:
            for folder_name, sub_folders, file_names in os.walk(content_path):
                for file_name in file_names:
                    file_path = os.path.join(folder_name, file_name)

                    # 验证文件是否可读
                    if not validate_file_access(file_path):
                        return False

                    # 计算在zip中的路径（去掉content目录本身）
                    arc_name = os.path.relpath(file_path, content_path)

                    try:
                        zip_file.write(file_path, arc_name)
                    except Exception as e:
                        print(f"错误: 无法将文件添加到zip: {file_path}")
                        print(f"详细错误: {e}")
                        return False

        # 验证zip文件是否成功创建且不为空
        if not os.path.exists(zip_path):
            print(f"错误: zip文件创建失败: {zip_path}")
            return False

        if os.path.getsize(zip_path) == 0:
            print(f"错误: 创建的zip文件为空: {zip_path}")
            return False

        return True

    except Exception as e:
        print(f"错误: 创建zip文件失败: {zip_path}")
        print(f"详细错误: {e}")
        return False


def delete_with_force(path):
    """使用Windows命令行强制删除"""
    if os.path.exists(path):
        # 使用rd命令强制删除目录
        cmd = f'rd /s /q "{path}"'
        try:
            subprocess.run(cmd, shell=True, check=True)
            print(f"强制删除成功: {path}")
        except subprocess.CalledProcessError as e:
            print(f"删除失败: {e}")
            # 或者使用del命令
            cmd = f'del /f /s /q "{path}\\*.*"'
            subprocess.run(cmd, shell=True)
            os.rmdir(path)
    else:
        print(f"路径不存在: {path}")

def delete_directory_with_retry(directory_path, max_retries=3):
    """带重试机制的目录删除"""
    for attempt in range(max_retries):
        try:
            delete_with_force(directory_path)
            print(f"✓ 已删除: {directory_path} (尝试 {attempt + 1}/{max_retries})")
            return True

        except Exception as e:
            if attempt < max_retries - 1:
                # 计算等待时间：第一次1秒，第二次5秒
                wait_time = 1 if attempt == 0 else 5
                print(f"删除失败，等待 {wait_time} 秒后重试... (错误: {e})")
                time.sleep(wait_time)
            else:
                print(f"错误: 无法删除目录: {directory_path}")
                print(f"详细错误: {e}")
                return False

    return False


def process_content_directory(content_path):
    """处理单个content目录"""
    parent_dir = os.path.dirname(content_path)
    zip_path = os.path.join(parent_dir, 'content.zip')

    print(f"正在处理: {content_path}")

    # 创建zip文件
    if not create_content_zip(content_path, zip_path):
        return False

    print(f"✓ 已成功创建: {zip_path}")
    print(f"  文件大小: {os.path.getsize(zip_path) / 1024 / 1024:.2f} MB")

    # 删除原目录
    if not delete_directory_with_retry(content_path):
        return False

    # 验证目录是否成功删除
    if os.path.exists(content_path):
        print(f"错误: 目录删除后仍然存在: {content_path}")
        return False

    return True


def package_setup_mods(mod_dir):
    """
    递归遍历mod_dir下的所有文件，找到content目录并打包为仅存储（不压缩）的zip
    生产部署脚本：任何错误都会导致立即返回False

    参数:
        mod_dir: 要遍历的根目录路径

    返回:
        bool: True表示所有操作成功完成，False表示遇到错误
    """
    # 验证输入目录
    if not validate_directory(mod_dir):
        return False

    try:
        # 遍历目录
        for root_dir, dirs_list, files_list in os.walk(mod_dir, topdown=True):
            # 检查当前目录是否有名为'content'的子目录（不区分大小写）
            content_dirs = [d for d in dirs_list if d.lower() == 'content']

            for content_dir_name in content_dirs:
                content_path = os.path.join(root_dir, content_dir_name)

                # 处理当前content目录
                if not process_content_directory(content_path):
                    return False

                # 从dirs列表中移除content目录，防止继续遍历
                if content_dir_name in dirs_list:
                    dirs_list.remove(content_dir_name)

    except KeyboardInterrupt:
        print("\n错误: 用户中断操作")
        return False
    except Exception as e:
        print(f"错误: 遍历目录时发生意外错误")
        print(f"详细错误: {e}")
        return False

    print(f"\n✓ 所有处理完成!")
    return True


# 示例使用方式
if __name__ == "__main__":
    # 测试路径 - 请修改为您实际的路径
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_dir = os.path.join(base_dir, "files", "Mods")
    # 如果测试路径存在，则执行函数
    if os.path.exists(test_dir):
       succ = package_setup_mods(test_dir)
       print("打包%s！" % "成功" if succ else "失败")
    else:
        print(f"目录不存在: {test_dir}")
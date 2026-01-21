import os
import shlex
import time
import subprocess
import base64
import binascii


def get_encryption_password():
    """获取加密密码，通过环境变量计算"""
    # 获取环境变量
    mod_password = os.environ.get('MOD_PASSWORD')
    mod_password_mask = os.environ.get('MOD_PASSWORD_MASK')

    if not mod_password or not mod_password_mask:
        print("错误: 缺少必要的环境变量 MOD_PASSWORD 或 MOD_PASSWORD_MASK")
        return None

    try:
        # 1. 对MOD_PASSWORD进行base64解码
        decoded_password = base64.b64decode(mod_password)
        password_binary = decoded_password

        # 2. 对MOD_PASSWORD_MASK进行十六进制解码
        # 先移除可能的0x前缀和空格
        mask_hex = mod_password_mask.strip()
        if mask_hex.startswith('0x'):
            mask_hex = mask_hex[2:]
        mask_hex = mask_hex.replace(' ', '')

        # 十六进制字符串转二进制
        mask_binary = binascii.unhexlify(mask_hex)

        # 使用循环mask进行异或运算
        # 当mask长度不足时，自动循环使用
        xor_result = bytes([password_binary[i] ^ mask_binary[i % len(mask_binary)]
                            for i in range(len(password_binary))])

        # 5. 将结果转换为字符串（假设结果为UTF-8编码）
        final_password = xor_result.decode('utf-8')

        return final_password

    except Exception as e:
        print(f"错误: 计算加密密码时发生错误")
        print(f"详细错误: {e}")
        return None


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





def create_content_zip(content_path, zip_path, password=None):
    """
    使用固定路径的 7-Zip 创建 zip：
    - content_path 这一层不进入 zip
    - 仅存储（-mx=0）
    - 有 password 时使用 ZipCrypto
    - 使用固定路径: C:\\Program Files\\7-Zip\\7z.exe
    """

    seven_zip_path = r"C:\Program Files\7-Zip\7z.exe"

    if not os.path.isfile(seven_zip_path):
        print(f"未找到 7-Zip: {seven_zip_path}")
        return False

    content_path = os.path.abspath(content_path)
    zip_path = os.path.abspath(zip_path)

    # 防止把输出 zip 打包进去
    if os.path.commonpath([zip_path, content_path]) == content_path:
        print("zip_path 不能位于 content_path 目录内部，否则会被递归打包")
        return False

    cmd = [
        seven_zip_path,
        "a",            # add
        "-tzip",        # zip 格式
        "-mx=0",        # 仅存储
        "-y",           # 自动 yes
    ]

    if  password:
        cmd.append(f"-p{password}")
        cmd.append("-mem=ZipCrypto")   # 强制传统 ZipCrypto
        cmd.append("-mcu=on")

    cmd.append(zip_path)
    cmd.append(".")

    print(" ".join(cmd))

    result = subprocess.run(
        cmd,
        cwd=content_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        print(
            "7-Zip 打包失败:\n"
            f"cmd: {' '.join(shlex.quote(c) for c in cmd)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        return False
    return True

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


def process_content_directory(content_path, use_encryption=False, password=None):
    """处理单个content目录"""
    parent_dir = os.path.dirname(content_path)
    zip_path = os.path.join(parent_dir, 'content.zip')

    print(f"正在处理: {content_path}")
    if use_encryption:
        print(f"使用加密打包，密码长度: {len(password) if password else 0}")

    # 创建zip文件
    if not create_content_zip(content_path, zip_path, password):
        return False

    print(f"✓ 已成功创建: {zip_path}")
    print(f"  文件大小: {os.path.getsize(zip_path) / 1024 / 1024:.2f} MB")

    if use_encryption:
        print(f"  加密方式: ZipCrypto")

    # 删除原目录
    if not delete_directory_with_retry(content_path):
        return False

    # 验证目录是否成功删除
    if os.path.exists(content_path):
        print(f"错误: 目录删除后仍然存在: {content_path}")
        return False

    return True


def is_in_need_encryption_dirs(path, mod_dir):
    """检查当前路径是否在需要加密的目录下"""
    # 获取相对于mod_dir的相对路径
    relative_path = os.path.relpath(path, mod_dir)

    # 分割路径为各个部分
    path_parts = relative_path.split(os.sep)

    # 检查路径的任一部分是否需要加密
    need_encryption_dirs = {'new-chinese-mods', 'third-upgrades-archer', 'the-great-expansion'}
    for path_part in path_parts:
        if path_part.lower() in need_encryption_dirs :
         return True

    return False


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

    # 预加载加密密码（只需要计算一次）
    encryption_password = get_encryption_password()


    try:
        # 遍历目录
        for root_dir, dirs_list, files_list in os.walk(mod_dir, topdown=True):
            # 检查当前路径是否在new-chinese-mods目录下
            use_encryption = is_in_need_encryption_dirs(root_dir, mod_dir) and encryption_password is not None

            # 检查当前目录是否有名为content的子目录（不区分大小写）
            content_dirs = [d for d in dirs_list if d.lower() == 'content']

            for content_dir_name in content_dirs:
                content_path = os.path.join(root_dir, content_dir_name)

                # 处理当前content目录
                if not process_content_directory(content_path, use_encryption, encryption_password if use_encryption else None):
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
        print("打包%s！" % ("成功" if succ else "失败"))
    else:
        print(f"目录不存在: {test_dir}")
import re
import requests
import json
from urllib.parse import urlparse, parse_qs
import os
import subprocess
import shutil
import time
import sys


def get_video_info(bvid):
    """获取视频信息（标题和简介）"""
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.bilibili.com/"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data["code"] != 0:
            print(f"API错误: {data.get('message', '未知错误')}")
            return None, None

        title = data["data"]["title"]
        desc = data["data"]["desc"]
        return title, desc
    except Exception as e:
        print(f"获取视频信息失败: {str(e)}")
        return None, None


def get_video_comments(bvid, max_comments=20):
    """获取视频评论"""
    # 获取视频aid
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.bilibili.com/"
    }

    try:
        # 获取视频aid
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data["code"] != 0:
            print(f"API错误: {data.get('message', '未知错误')}")
            return "无法获取评论"

        aid = data["data"]["aid"]

        # 获取评论
        comment_url = f"https://api.bilibili.com/x/v2/reply?pn=1&type=1&oid={aid}&sort=2"
        response = requests.get(comment_url, headers=headers, timeout=15)
        response.raise_for_status()
        comment_data = response.json()

        if comment_data["code"] != 0:
            print(f"评论API错误: {comment_data.get('message', '未知错误')}")
            return "无法获取评论"

        comments = []
        for i, reply in enumerate(comment_data["data"]["replies"][:max_comments]):
            user = reply["member"]["uname"]
            content = reply["content"]["message"]
            comments.append(f"{i + 1}. {user}: {content}")

        return "\n".join(comments)
    except Exception as e:
        print(f"获取评论失败: {str(e)}")
        return "无法获取评论"


def extract_bvid(video_url):
    """从URL中提取BVID - 更健壮的版本"""
    # 尝试直接匹配BV号
    bvid_match = re.search(r"BV[0-9A-Za-z]{10}", video_url)
    if bvid_match:
        return bvid_match.group(0)

    # 尝试解析URL参数
    parsed = urlparse(video_url)
    query = parse_qs(parsed.query)

    # 优先从查询参数中获取
    if "bvid" in query:
        return query["bvid"][0]

    # 尝试从路径中提取
    path_parts = parsed.path.split("/")
    if "video" in path_parts:
        video_index = path_parts.index("video") + 1
        if video_index < len(path_parts):
            bvid_candidate = path_parts[video_index]
            if bvid_candidate.startswith("BV") and len(bvid_candidate) == 12:
                return bvid_candidate

    # 最后尝试匹配短链接中的BV号
    short_match = re.search(r"b23.tv/[a-zA-Z0-9]+", video_url)
    if short_match:
        short_url = "https://" + short_match.group(0)
        try:
            response = requests.get(short_url, allow_redirects=True, timeout=10)
            if response.status_code == 200:
                return extract_bvid(response.url)
        except:
            pass

    return None


def install_yt_dlp():
    """自动安装yt-dlp"""
    try:
        print("正在安装yt-dlp...")
        subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp"], check=True)
        print("yt-dlp安装成功！")
        return True
    except Exception as e:
        print(f"自动安装失败: {e}")
        return False


def download_ffmpeg():
    """下载ffmpeg到当前目录"""
    try:
        print("正在下载ffmpeg...")
        # 下载ffmpeg便携版
        url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        
        # 保存zip文件
        with open("ffmpeg.zip", "wb") as f:
            f.write(response.content)
        
        # 解压
        import zipfile
        with zipfile.ZipFile("ffmpeg.zip", 'r') as zip_ref:
            zip_ref.extractall(".")
        
        # 找到ffmpeg.exe并移动到当前目录
        for root, dirs, files in os.walk("."):
            if "ffmpeg.exe" in files:
                src = os.path.join(root, "ffmpeg.exe")
                shutil.move(src, "./ffmpeg.exe")
                break
                
        # 清理
        os.remove("ffmpeg.zip")
        shutil.rmtree("ffmpeg-master-latest-win64-gpl", ignore_errors=True)
        
        print("ffmpeg下载成功！")
        return True
    except Exception as e:
        print(f"ffmpeg下载失败: {e}")
        return False


def download_yt_dlp_exe():
    """下载yt-dlp.exe到当前目录"""
    try:
        print("正在下载yt-dlp.exe...")
        url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open("yt-dlp.exe", "wb") as f:
            f.write(response.content)
        print("yt-dlp.exe下载成功！")
        return True
    except Exception as e:
        print(f"下载失败: {e}")
        return False


def audio_to_text(video_url):
    """使用本地语音识别转换音频（优化版）"""
    try:
        # 检查是否安装了yt-dlp
        yt_dlp_path = shutil.which("yt-dlp")
        if not yt_dlp_path:
            # 尝试使用系统路径中的yt-dlp
            yt_dlp_path = "yt-dlp"
            if not shutil.which(yt_dlp_path):
                # 如果在Windows上，尝试当前目录的yt-dlp.exe
                if sys.platform == "win32":
                    if os.path.exists("yt-dlp.exe"):
                        yt_dlp_path = "yt-dlp.exe"
                    else:
                        # 尝试下载yt-dlp.exe
                        if download_yt_dlp_exe():
                            yt_dlp_path = "yt-dlp.exe"
                        else:
                            return "无法获取yt-dlp工具，请手动下载yt-dlp.exe并放在当前目录"
                else:
                    # 尝试通过pip安装
                    if install_yt_dlp():
                        yt_dlp_path = "yt-dlp"
                    else:
                        return "请手动安装yt-dlp: pip install yt-dlp"

        # 创建临时目录
        os.makedirs("temp", exist_ok=True)
        audio_path = os.path.join("temp", "audio.wav")

        print("正在下载音频...")
        # 检查是否需要ffmpeg
        ffmpeg_path = ""
        if os.path.exists("ffmpeg.exe"):
            ffmpeg_path = os.path.abspath("ffmpeg.exe")
        elif not shutil.which("ffmpeg"):
            # 尝试下载ffmpeg
            if sys.platform == "win32" and download_ffmpeg():
                ffmpeg_path = os.path.abspath("ffmpeg.exe")
        
        # 构建yt-dlp命令
        cmd = [
            yt_dlp_path,
            "-x",  # 只提取音频
            "--audio-format", "wav",
            "--audio-quality", "0",  # 最佳质量
            "--no-playlist",
            "-o", audio_path,
            video_url
        ]
        
        # 如果有本地ffmpeg，指定路径
        if ffmpeg_path:
            cmd.extend(["--ffmpeg-location", ffmpeg_path])
        
        # 下载音频
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else "未知错误"
            return f"下载失败: {error_msg}"

        # 检查文件大小
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            return "音频下载失败"

        print(f"音频下载完成，大小: {os.path.getsize(audio_path) // 1024}KB")

        # 使用本地语音识别
        try:
            import whisper
        except ImportError:
            print("正在安装Whisper语音识别库...")
            subprocess.run([sys.executable, "-m", "pip", "install", "openai-whisper", "torch", "torchaudio"],
                           check=True)
            import whisper

        # 使用小模型进行识别
        model = whisper.load_model("small")
        print("正在识别语音...")
        result = model.transcribe(audio_path)

        # 清理临时文件
        os.remove(audio_path)
        return result["text"]

    except Exception as e:
        return f"处理失败: {str(e)}"


def main():
    print("B站视频信息提取工具")
    video_url = input("请输入B站视频链接: ").strip()

    # 提取BVID
    bvid = extract_bvid(video_url)

    if not bvid or not bvid.startswith("BV"):
        print("无法从链接中提取BV号，请检查链接格式")
        print(f"原始链接: {video_url}")
        return

    print("\n正在获取视频信息...")
    title, desc = get_video_info(bvid)

    if not title:
        print("获取视频信息失败，请检查链接是否正确")
        return

    print("\n" + "=" * 50)
    print(f"标题: {title}")
    print("\n简介:")
    print(desc)
    print("=" * 50)

    print("\n正在获取评论...")
    comments = get_video_comments(bvid)
    print("\n热门评论:")
    print(comments)
    print("=" * 50)

    # 直接进行语音转文字
    print("\n正在下载音频并进行语音识别...")
    print("(此过程可能需要几分钟，请耐心等待...)")
    start_time = time.time()

    audio_text = audio_to_text(video_url)

    print(f"\n处理完成 (耗时: {time.time() - start_time:.1f}秒)")
    print("\n语音转文字结果:")
    print(audio_text[:5000] + ("..." if len(audio_text) > 5000 else ""))

    # 可选：将完整结果保存到文件
    save_file = input("\n是否保存完整结果到文件？(y/n): ").strip().lower()
    if save_file == "y":
        filename = f"{bvid}_transcription.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"视频标题: {title}\n\n")
            f.write(f"简介:\n{desc}\n\n")
            f.write(f"热门评论:\n{comments}\n\n")
            f.write(f"语音转文字结果:\n{audio_text}")
        print(f"结果已保存到 {filename}")


if __name__ == "__main__":
    main()
"""
daily_stock_analysis 多渠道推送模块示例

参考: https://github.com/wanrenhuifu/daily_stock_analysis

支持的推送渠道:
1. 飞书 (Feishu)
2. 企业微信 (WeCom)
3. Telegram
4. Discord
5. 邮件 (Email)
6. Slack
"""

import os
import json
import asyncio
import aiohttp
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib


# ==================== 推送消息基类 ====================

@dataclass
class PushMessage:
    """推送消息结构"""
    title: str
    content: str
    stock_code: Optional[str] = None
    signal: Optional[str] = None  # BUY/HOLD/SELL


# ==================== 推送渠道接口 ====================

class NotificationChannel(ABC):
    """推送渠道抽象基类"""
    
    @abstractmethod
    async def send(self, message: PushMessage) -> bool:
        """发送消息"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查渠道是否可用"""
        pass


# ==================== 飞书推送 ====================

class FeishuNotifier(NotificationChannel):
    """飞书WebHook推送"""
    
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or os.getenv("FEISHU_WEBHOOK_URL")
        self.secret = os.getenv("FEISHU_SECRET")  # 可选的签名密钥
    
    def is_available(self) -> bool:
        return bool(self.webhook_url)
    
    async def send(self, message: PushMessage) -> bool:
        """发送飞书消息"""
        if not self.is_available():
            return False
        
        # 构建飞书消息格式
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": message.title},
                    "template": self._get_signal_color(message.signal)
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": message.content
                        }
                    }
                ]
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    return resp.status == 200
        except Exception as e:
            print(f"飞书推送失败: {e}")
            return False
    
    def _get_signal_color(self, signal: Optional[str]) -> str:
        """根据信号类型返回颜色"""
        colors = {
            "BUY": "green",
            "HOLD": "yellow",
            "SELL": "red",
            None: "blue"
        }
        return colors.get(signal, "blue")


# ==================== 企业微信推送 ====================

class WeComNotifier(NotificationChannel):
    """企业微信WebHook推送"""
    
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or os.getenv("WECOM_WEBHOOK_URL")
    
    def is_available(self) -> bool:
        return bool(self.webhook_url)
    
    async def send(self, message: PushMessage) -> bool:
        """发送企业微信消息"""
        if not self.is_available():
            return False
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"### {message.title}\n\n{message.content}"
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    return resp.status == 200
        except Exception as e:
            print(f"企业微信推送失败: {e}")
            return False


# ==================== Telegram推送 ====================

class TelegramNotifier(NotificationChannel):
    """Telegram Bot推送"""
    
    def __init__(
        self,
        bot_token: str = None,
        chat_id: str = None
    ):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
    
    def is_available(self) -> bool:
        return bool(self.bot_token and self.chat_id)
    
    async def send(self, message: PushMessage) -> bool:
        """发送Telegram消息"""
        if not self.is_available():
            return False
        
        # Telegram不支持复杂Markdown，使用HTML
        content = message.content.replace("\n", "\n\n")
        
        payload = {
            "chat_id": self.chat_id,
            "text": f"*{message.title}*\n\n{content}",
            "parse_mode": "Markdown"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    return resp.status == 200
        except Exception as e:
            print(f"Telegram推送失败: {e}")
            return False


# ==================== Discord推送 ====================

class DiscordNotifier(NotificationChannel):
    """Discord WebHook推送"""
    
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
    
    def is_available(self) -> bool:
        return bool(self.webhook_url)
    
    async def send(self, message: PushMessage) -> bool:
        """发送Discord消息"""
        if not self.is_available():
            return False
        
        # 根据信号类型选择颜色
        colors = {
            "BUY": 0x00FF00,    # 绿色
            "HOLD": 0xFFFF00,   # 黄色
            "SELL": 0xFF0000,   # 红色
            None: 0x0000FF     # 蓝色
        }
        
        payload = {
            "embeds": [{
                "title": message.title,
                "description": message.content,
                "color": colors.get(message.signal, 0x0000FF)
            }]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    return resp.status == 200
        except Exception as e:
            print(f"Discord推送失败: {e}")
            return False


# ==================== 邮件推送 ====================

class EmailNotifier(NotificationChannel):
    """邮件推送"""
    
    def __init__(
        self,
        smtp_host: str = None,
        smtp_port: int = 587,
        smtp_user: str = None,
        smtp_password: str = None,
        from_addr: str = None,
        to_addrs: List[str] = None
    ):
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.from_addr = from_addr or os.getenv("EMAIL_FROM", self.smtp_user)
        self.to_addrs = to_addrs or os.getenv("EMAIL_TO", "").split(",")
    
    def is_available(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)
    
    async def send(self, message: PushMessage) -> bool:
        """发送邮件"""
        if not self.is_available():
            return False
        
        # 构建邮件
        msg = MIMEMultipart('alternative')
        msg['Subject'] = message.title
        msg['From'] = self.from_addr
        msg['To'] = ', '.join(self.to_addrs)
        
        # HTML内容
        html_content = f"""
        <html>
        <body>
            <h2>{message.title}</h2>
            <pre>{message.content}</pre>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(message.content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        try:
            # 同步发送邮件
            await asyncio.to_thread(
                self._send_sync,
                msg
            )
            return True
        except Exception as e:
            print(f"邮件推送失败: {e}")
            return False
    
    def _send_sync(self, msg):
        """同步发送邮件"""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)


# ==================== 推送管理器 ====================

class NotificationManager:
    """多渠道推送管理器"""
    
    def __init__(self):
        self.channels: List[NotificationChannel] = []
        self._init_channels()
    
    def _init_channels(self):
        """初始化所有可用渠道"""
        # 飞书
        feishu = FeishuNotifier()
        if feishu.is_available():
            self.channels.append(feishu)
        
        # 企业微信
        wecom = WeComNotifier()
        if wecom.is_available():
            self.channels.append(wecom)
        
        # Telegram
        telegram = TelegramNotifier()
        if telegram.is_available():
            self.channels.append(telegram)
        
        # Discord
        discord = DiscordNotifier()
        if discord.is_available():
            self.channels.append(discord)
        
        # 邮件
        email = EmailNotifier()
        if email.is_available():
            self.channels.append(email)
    
    @property
    def available_channels(self) -> List[str]:
        """获取可用渠道列表"""
        return [type(ch).__name__.replace("Notifier", "") for ch in self.channels]
    
    async def send_all(self, message: PushMessage) -> dict:
        """向所有渠道发送消息"""
        results = {}
        
        for channel in self.channels:
            channel_name = type(channel).__name__.replace("Notifier", "")
            success = await channel.send(message)
            results[channel_name] = success
            print(f"{channel_name}: {'✅成功' if success else '❌失败'}")
        
        return results
    
    async def send_first_available(self, message: PushMessage) -> bool:
        """发送给第一个可用的渠道"""
        for channel in self.channels:
            if await channel.send(message):
                return True
        return False


# ==================== 示例使用 ====================

async def main():
    # 创建推送消息
    message = PushMessage(
        title="📊 2026-04-13 决策仪表盘",
        content="""
🟢 买入 | 贵州茅台(600519)
📌 缩量回踩MA5支撑，乖离率1.2%处于最佳买点
💰 狙击: 买入1780 | 止损1728 | 目标1922
✅多头排列 ✅乖离安全 ✅量能配合
        """.strip(),
        stock_code="600519",
        signal="BUY"
    )
    
    # 创建推送管理器
    manager = NotificationManager()
    
    print(f"可用渠道: {manager.available_channels}")
    
    # 发送消息
    if manager.channels:
        results = await manager.send_all(message)
        print(f"\n发送结果: {results}")
    else:
        print("没有配置任何推送渠道")


if __name__ == "__main__":
    asyncio.run(main())

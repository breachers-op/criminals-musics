"""
Pyrogram String Session Generator
Run this in the Replit Shell: python generate_session.py
"""

import asyncio
from pyrogram import Client
from pyrogram.errors import (
    SessionPasswordNeeded,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    PhoneNumberInvalid,
    BadRequest,
)


BANNER = """
╔══════════════════════════════════════════╗
║   Pyrogram String Session Generator     ║
║   For use with Telegram Userbots        ║
╚══════════════════════════════════════════╝
"""


async def generate_session():
    print(BANNER)
    print("You need your API ID and API Hash from https://my.telegram.org\n")

    try:
        api_id_input = input("Enter your API ID  : ").strip()
        api_id = int(api_id_input)
    except ValueError:
        print("❌ API ID must be a number. Exiting.")
        return

    api_hash = input("Enter your API Hash : ").strip()
    if not api_hash:
        print("❌ API Hash cannot be empty. Exiting.")
        return

    phone = input("Enter phone number (with country code e.g. +919876543210): ").strip()
    if not phone.startswith("+"):
        print("⚠️  Phone number should start with country code e.g. +91...")
        phone = "+" + phone

    print("\n🔄 Connecting to Telegram...")

    client = Client(
        name="session_gen",
        api_id=api_id,
        api_hash=api_hash,
        in_memory=True,
    )

    try:
        await client.connect()
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return

    try:
        sent = await client.send_code(phone)
    except PhoneNumberInvalid:
        print("❌ Invalid phone number. Please check and try again.")
        await client.disconnect()
        return
    except Exception as e:
        print(f"❌ Error sending OTP: {e}")
        await client.disconnect()
        return

    print("✅ OTP sent to your Telegram account.")
    otp = input("Enter the OTP (separate digits with space if needed): ").strip().replace(" ", "")

    try:
        await client.sign_in(phone, sent.phone_code_hash, otp)

    except PhoneCodeInvalid:
        print("❌ Invalid OTP. Please try again.")
        await client.disconnect()
        return

    except PhoneCodeExpired:
        print("❌ OTP expired. Please run the script again.")
        await client.disconnect()
        return

    except SessionPasswordNeeded:
        print("\n🔒 Two-step verification is enabled on your account.")
        password = input("Enter your 2FA password: ").strip()
        try:
            await client.check_password(password)
        except BadRequest:
            print("❌ Wrong password. Please try again.")
            await client.disconnect()
            return
        except Exception as e:
            print(f"❌ Error checking password: {e}")
            await client.disconnect()
            return

    except Exception as e:
        print(f"❌ Sign-in error: {e}")
        await client.disconnect()
        return

    string_session = await client.export_session_string()
    me = await client.get_me()
    await client.disconnect()

    print("\n" + "=" * 50)
    print(f"✅ Logged in as: {me.first_name} (@{me.username or 'no username'})")
    print("=" * 50)
    print("\n🔑 YOUR STRING SESSION (copy everything between the quotes):\n")
    print(f'STRING_SESSION = "{string_session}"')
    print("\n" + "=" * 50)
    print("⚠️  IMPORTANT:")
    print("  • Never share this string with anyone.")
    print("  • Add it as a secret in Replit: STRING_SESSION")
    print("  • Treat it like your account password.")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(generate_session())

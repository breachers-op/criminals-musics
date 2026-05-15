from pyrogram import Client
import asyncio

API_ID = int(input("Enter API_ID: "))
API_HASH = input("Enter API_HASH: ")
PHONE_NUMBER = input("Enter Phone Number: ")


async def main():

    app = Client(
        "session",
        api_id=API_ID,
        api_hash=API_HASH,
        phone_number=PHONE_NUMBER,
        in_memory=True
    )

    await app.start()

    me = await app.get_me()

    print(f"\nLogged in as {me.first_name}")

    session = await app.export_session_string()

    print("\nYour Session String:\n")
    print(session)

    await app.stop()


asyncio.run(main())

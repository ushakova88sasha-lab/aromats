import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from dotenv import load_dotenv
from database import Database

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

AROMAS = [
    "Красное вино", "Мамины объятия", "Земля", "Запах денег",
    "Яблочный апероль", "Груша в бренди", "Бурбон со сливками",
    "Кашемир и мускус", "Плитка шоколада", "Конопляное масло",
    "Патрики", "Холодил. в цветоч."
]

MONEY_AROMA_INDEX = 3
MONEY_VARIANTS = ["Книжный переплет", "Кожа и амбра"]

IMAGES_DIR = r"C:\Users\Sana\Desktop\картинки ароматов"
AROMA_IMAGES = {
    "Красное вино":        "Красное вино.jpg",
    "Мамины объятия":      "Мамины объятия.jpg",
    "Земля":               "Земля.jpg",
    "Запах денег":         "Запах денег.jpg",
    "Яблочный апероль":    "Яблочный Апероль.jpg",
    "Груша в бренди":      "Груша в бренди.jpg",
    "Бурбон со сливками":  "Бурбон со сливками.jpg",
    "Кашемир и мускус":    "Кашемир и мускус.jpg",
    "Плитка шоколада":     "Плитка шоколада.jpg",
    "Конопляное масло":    "Конопляное масло.jpg",
    "Патрики":             "Патрики.jpg",
    "Холодил. в цветоч.":  "Холодильник в цветочном.jpg",
}


def get_photo(aroma: str) -> FSInputFile:
    return FSInputFile(os.path.join(IMAGES_DIR, AROMA_IMAGES[aroma]))


class Survey(StatesGroup):
    select_aroma = State()
    select_money_variant = State()
    rate_like = State()
    rate_bright = State()
    room = State()


def aroma_keyboard(rated: list) -> InlineKeyboardMarkup:
    available = [(i, name) for i, name in enumerate(AROMAS) if i not in rated]
    rows = []
    for j in range(0, len(available), 2):
        row = [InlineKeyboardButton(text=available[j][1], callback_data=f"aroma:{available[j][0]}")]
        if j + 1 < len(available):
            row.append(InlineKeyboardButton(text=available[j + 1][1], callback_data=f"aroma:{available[j + 1][0]}"))
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def money_variant_keyboard() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text=v, callback_data=f"variant:{i}") for i, v in enumerate(MONEY_VARIANTS)]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def rating_keyboard(prefix: str) -> InlineKeyboardMarkup:
    row1 = [InlineKeyboardButton(text=str(i), callback_data=f"{prefix}:{i}") for i in range(1, 6)]
    row2 = [InlineKeyboardButton(text=str(i), callback_data=f"{prefix}:{i}") for i in range(6, 11)]
    return InlineKeyboardMarkup(inline_keyboard=[row1, row2])


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database()


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(Survey.select_aroma)
    await state.update_data(rated=[])
    await message.answer("Выберите аромат:", reply_markup=aroma_keyboard([]))


@dp.callback_query(Survey.select_aroma, F.data.startswith("aroma:"))
async def aroma_selected(callback: CallbackQuery, state: FSMContext):
    index = int(callback.data.split(":")[1])
    aroma = AROMAS[index]
    await state.update_data(aroma=aroma, aroma_index=index)
    await callback.message.delete()

    if index == MONEY_AROMA_INDEX:
        await callback.message.answer_photo(
            photo=get_photo(aroma),
            caption="Какой больше подходит для запаха денег?",
            reply_markup=money_variant_keyboard()
        )
        await state.set_state(Survey.select_money_variant)
        await callback.answer()
        return

    photo_msg = await callback.message.answer_photo(
        photo=get_photo(aroma),
        caption=f"На сколько тебе понравился аромат «{aroma}» 👇✍️",
        reply_markup=rating_keyboard("like")
    )
    await state.update_data(photo_msg_id=photo_msg.message_id)
    await state.set_state(Survey.rate_like)
    await callback.answer()


@dp.callback_query(Survey.select_money_variant, F.data.startswith("variant:"))
async def money_variant_selected(callback: CallbackQuery, state: FSMContext):
    variant_index = int(callback.data.split(":")[1])
    variant = MONEY_VARIANTS[variant_index]
    data = await state.get_data()
    rated = data.get("rated", [])
    rated.append(MONEY_AROMA_INDEX)

    await db.save_response(
        user_id=callback.from_user.id,
        username=callback.from_user.username or "",
        aroma="Запах денег",
        variant=variant
    )
    await callback.message.edit_caption(caption=f"Запах денег — ваш выбор: {variant}")

    if len(rated) == len(AROMAS):
        await state.clear()
        await callback.message.answer("Вы оценили все ароматы! Спасибо 🙏")
    else:
        await state.update_data(rated=rated)
        await state.set_state(Survey.select_aroma)
        await callback.message.answer("Выберите следующий аромат 👇", reply_markup=aroma_keyboard(rated))

    await callback.answer()


@dp.message(Survey.rate_like)
async def rate_like_wrong(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, выберите оценку с помощью кнопок 👆")


@dp.message(Survey.rate_bright)
async def rate_bright_wrong(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, выберите оценку с помощью кнопок 👆")


@dp.callback_query(Survey.rate_like, F.data.startswith("like:"))
async def rate_like(callback: CallbackQuery, state: FSMContext):
    score = int(callback.data.split(":")[1])
    data = await state.get_data()
    aroma = data["aroma"]
    await state.update_data(like=score)
    await callback.message.edit_caption(caption=f"Аромат «{aroma}» понравился {score}/10")
    await callback.message.answer(
        f"На сколько для тебя яркий аромат «{aroma}»? 🫦👇",
        reply_markup=rating_keyboard("bright")
    )
    await state.set_state(Survey.rate_bright)
    await callback.answer()


@dp.callback_query(Survey.rate_bright, F.data.startswith("bright:"))
async def rate_bright(callback: CallbackQuery, state: FSMContext):
    score = int(callback.data.split(":")[1])
    data = await state.get_data()
    aroma = data["aroma"]
    await state.update_data(bright=score)
    await callback.message.edit_text(f"Яркость «{aroma}»: {score}/10")
    await callback.message.answer(
        f"В какую комнату вы бы поставили аромат «{aroma}»?\nНапишите словами ниже 👇"
    )
    await state.set_state(Survey.room)
    await callback.answer()


@dp.message(Survey.room)
async def room_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    rated = data.get("rated", [])
    rated.append(data["aroma_index"])

    aroma = data["aroma"]
    like = data["like"]
    bright = data["bright"]
    room = message.text
    photo_msg_id = data.get("photo_msg_id")

    await db.save_response(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        aroma=aroma,
        like=like,
        bright=bright,
        room=room
    )

    summary = (
        f"Аромат — «{aroma}»:\n"
        f"👍 Понравился: {like}/10\n"
        f"✨ Яркость: {bright}/10\n"
        f"🏠 Комната: {room}"
    )
    if photo_msg_id:
        try:
            await bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=photo_msg_id,
                caption=summary
            )
        except Exception:
            await message.answer(summary)
    else:
        await message.answer(summary)

    if len(rated) == len(AROMAS):
        await state.clear()
        await message.answer("Вы оценили все ароматы, спасибо за участие! 🙏")
    else:
        await state.update_data(rated=rated)
        await state.set_state(Survey.select_aroma)
        await message.answer("Выберите следующий аромат 👇", reply_markup=aroma_keyboard(rated))


async def main():
    await db.init()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import json
import os
import aiocron
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime, timezone, timedelta
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram import F 
from datetime import datetime 



TOKEN = "7834367258:AAEivjdI1roxgvnhEkgeKjln6_JP4TBY2HE"
ADMIN_ID = 5929134791  # Admin ID sini shu yerga yozing

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = dp  # Routerni alohida yaratmasdan, dp o'zidan foydalanamiz

# JSON fayl nomlari
USER_PROFILES_FILE = "user_profiles.json"
CONTESTS_FILE = "contests.json"
QUESTIONS_FILE = "questions.json"
participants = "participants.json"

# 📥 JSON fayldan ma'lumotlarni yuklash
def load_json(file_name):
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

# 📤 JSON faylga ma'lumotlarni saqlash
def save_json(file_name, data):
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)



# 🟢 Ma'lumotlarni yuklash
user_profiles = load_json(USER_PROFILES_FILE)
contests = load_json(CONTESTS_FILE)
questions = load_json(QUESTIONS_FILE)

# ✅ Holatlar uchun FSM
class RegisterState(StatesGroup):
    full_name = State()
    school = State()

class ContestState(StatesGroup):
    name = State()
    grade = State()
    subject = State()

class AnswerState(StatesGroup):
    contest_id = State()
    answers = State()

class JoinContestState(StatesGroup):
    contest_id = State()
    answers = State()

# Asosiy menyu tugmalari
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Profile"), KeyboardButton(text="Register"), KeyboardButton(text="Javoblarni kiritish"),
        KeyboardButton(text="Foydalanuvchilar")]
    ],
    resize_keyboard=True
)



class QuestionState(StatesGroup):
    contest_id = State()
    questions = State()

class StopContestState(StatesGroup):
    contest_id = State()

# Contest yakunlanganligini saqlash uchun faylni yuklash
def load_finished_contests():
    try:
        with open("finished_contests.json", "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

finished_contests = load_finished_contests()
ghh = False
# Foydalanuvchi statistikasi uchun
try:
    with open("user_profiles.json", "r") as file:
        users_data = json.load(file)
except (FileNotFoundError, json.JSONDecodeError):
    users_data = {}

def get_participants_count(contest_id):
    try:
        with open("contest_results.json", "r") as file:
            contest_results = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0
    
    return len(contest_results.get(contest_id, []))

def update_ratings(contest_id):
    try:
        with open("contest_results.json", "r") as file:
            contest_results = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return
    
    results = contest_results.get(contest_id, [])
    participants_count = len(results)
    if participants_count == 0:
        return
    
    for idx, entry in enumerate(results, start=1):
        user_id = str(entry["user_id"])
        rank = idx
        score = (1 - (rank - 1) / participants_count) * 40
        
        if user_id not in users_data:
            users_data[user_id] = {"rating": 0, "contests_participated": 0}
        
        users_data[user_id]["rating"] += score
    
    with open("user_profiles.json", "w") as file:
        json.dump(users_data, file, indent=4)

# Javoblarni kiritish tugmasi uchun handler
@dp.message(F.text == "Javoblarni kiritish")
async def ask_contest_id(message: types.Message, state: FSMContext):
    await state.set_state(JoinContestState.contest_id)
    await message.answer("Iltimos, contest ID sini kiriting:")

# Contest ID kiritish handleri
@dp.message(JoinContestState.contest_id)
async def ask_answers(message: types.Message, state: FSMContext):
    contest_id = message.text

    # Agar contest allaqachon tugagan bo‘lsa
    if contest_id in finished_contests:
        await message.answer("⚠️ Bu contest allaqachon yakunlangan!")
        await state.clear()
        return

    await state.update_data(contest_id=contest_id)
    await state.set_state(JoinContestState.answers)
    await message.answer("Endi javoblarni kiriting (masalan: 1A, 2B, 3C ...):")

# Javoblarni qabul qilish va tekshirish
@dp.message(JoinContestState.answers)
async def check_answers(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    data = await state.get_data()
    contest_id = data["contest_id"]
    user_answers = message.text.strip()
    # Javoblar faylini yuklash
    try:
        with open("contest_results.json", "r") as file:
            contest_results = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        contest_results = {}
    

    # Foydalanuvchi oldin shu contestga javob yuborganmi?
    if contest_id in contest_results:
        # Agar mavjud contest noto‘g‘ri formatda bo‘lsa, uni tuzatamiz
        if not isinstance(contest_results[contest_id], list):
            contest_results[contest_id] = []

        # Har bir entry'ni dict ekanligini tekshiramiz va noto‘g‘ri bo‘lsa, tashlab yuboramiz
        contest_results[contest_id] = [
            entry for entry in contest_results[contest_id] if isinstance(entry, dict)
        ]

        for entry in contest_results[contest_id]:
            if entry.get("user_id") == user_id:
                await message.answer("⚠️ Siz ushbu contestga oldin javob yuborgansiz. Qayta yuborish mumkin emas!")
                await state.clear()
                return

    
    # To‘g‘ri javoblar ma'lumotlarini olish
    try:
        with open("answers.json", "r") as file:
            correct_answers = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        correct_answers = {}
    
    # Contest ID javoblar faylida bor-yo‘qligini tekshirish
    if contest_id not in correct_answers:
        await message.answer("⚠️ Bunday ID li contest uchun javoblar mavjud emas!")
        await state.clear()
        return

    correct_answers_list = correct_answers.get(contest_id, "").split(", ")
    user_answers_list = user_answers.split(", ")
    

    # To‘g‘ri javoblarni hisoblash
    correct_count = sum(1 for ua, ca in zip(user_answers_list, correct_answers_list) if ua == ca)
    
    # Natijalarni saqlash
    if contest_id not in contest_results:
        contest_results[contest_id] = []
    contest_results[contest_id].append({"user_id": user_id, "user_name": user_name, "correct_count": correct_count})
    
    # Natijalarni saralash
    contest_results[contest_id] = sorted(contest_results[contest_id], key=lambda x: x["correct_count"], reverse=True)
    
    users_data[str(user_id)]["contests_participated"] += 1
    
    with open("contest_results.json", "w") as file:
        json.dump(contest_results, file, indent=4)

    # Yangilangan user ma'lumotlarini saqlash
    with open("user_profiles.json", "w") as file:
        json.dump(users_data, file, indent=4)
    

    await message.answer(f"✅ Javoblaringiz qabul qilindi! Siz {correct_count} ta to‘g‘ri javob berdingiz.")
    ghh = True;
    await state.clear()

# Admin contestni to‘xtatish buyrug‘ini yuborganda
@dp.message(F.text == "/contest_stop")
async def stop_contest_command(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Siz admin emassiz!")
        return
    await state.set_state(StopContestState.contest_id)
    await message.answer("Yakunlanishi kerak bo‘lgan contest ID ni kiriting:")

# Admin contest ID ni kiritganda
@dp.message(StopContestState.contest_id)
async def stop_contest(message: types.Message, state: FSMContext):
    contest_id = message.text
    
    finished_contests[contest_id] = True
    with open("finished_contests.json", "w") as file:
        json.dump(finished_contests, file, indent=4)
    
    try:
        with open("contest_results.json", "r") as file:
            contest_results = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        contest_results = {}
    
    results = contest_results.get(contest_id, [])
    if not results:
        await message.answer("⚠️ Ushbu contest bo‘yicha hech qanday natijalar topilmadi!")
        await state.clear()
        return
    
    natijalar_text = "🏆 Contest natijalari:\n"
    for idx, entry in enumerate(results, start=1):
        natijalar_text += f"{idx}. {entry['user_name']} ---- {entry['correct_count']} ta to‘g‘ri javob\n"
    update_ratings(contest_id)
    await message.answer(natijalar_text)
    await state.clear()

# 1️⃣ Avval contest ID kiritishni tekshiradigan handler
@dp.message(AnswerState.contest_id)
async def process_answer_contest_id(message: types.Message, state: FSMContext):
    """ Contest ID ni tekshirish va javoblarni kiritishni so‘rash """
    contest_id = message.text.strip()

    if not contest_id.isdigit():
        await message.answer("❌ Contest ID faqat raqam bo‘lishi kerak! Iltimos, to‘g‘ri ID kiriting.")
        return

    if contest_id not in contests:
        await message.answer("❌ Xato! Bunday contest mavjud emas. Iltimos, to‘g‘ri ID kiriting.")
        return

    await state.update_data(contest_id=contest_id)
    await message.answer("✍️ Endi to‘g‘ri javoblarni kiriting (masalan: 1A 2C 3B ...):")
    await state.set_state(AnswerState.answers)



@dp.message(Command("start"))
async def start_handler(message: Message):
    user_id = str(message.from_user.id)
    full_name = message.from_user.full_name

    if user_id not in user_profiles:
        user_profiles[user_id] = {
            "id": user_id,
            "name": full_name,
            "school": None,
            "rating": 0,
            "contests_participated": 0
        }
        save_json(USER_PROFILES_FILE, user_profiles)

    await message.answer(
        f"Salom, {full_name}! Botga xush kelibsiz! ✅\n\n"
        "Ro‘yxatdan o‘tish uchun /register buyrug‘ini bering.\n\n"
        "Contest qo'shish uchun /add_contest xabarini yuboring (Admin). \n\n"
        "Agar biror Contest javoblarini yuklamoqchi bo'lsangiz /add_answers xabarini yuboring (Admin).",
        reply_markup=main_menu
    )

@dp.message(F.text == "Foydalanuvchilar")
async def show_users(message: types.Message):
    try:
        with open("user_profiles.json", "r") as file:
            users_data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        await message.answer("🚫 Hali hech qanday foydalanuvchi ma'lumoti mavjud emas!")
        return

    # Reyting bo‘yicha saralash
    sorted_users = sorted(users_data.items(), key=lambda x: x[1]["rating"], reverse=True)

    if not sorted_users:
        await message.answer("🚫 Hali hech qanday foydalanuvchi reytingga ega emas!")
        return

    # Foydalanuvchi darajasini aniqlash
    def get_rank(rating):
        if rating >= 2800:
            return "🟤 Legendary Grandmaster"
        elif rating >= 2200:
            return "⚫ Grandmaster"
        elif rating >= 1600:
            return "🔴 Master"
        elif rating >= 1000:
            return "🟠 Candidate Master"
        elif rating >= 600:
            return "🟣 Expert"
        elif rating >= 300:
            return "🔵 Specialist"
        elif rating >= 100:
            return "🟡 Pupil"
        else:
            return "🚼 Newbie"

    # Ro‘yxat shakllantirish
    users_list = "🏆 *Foydalanuvchilar reytingi:*\n\n"
    for idx, (user_id, data) in enumerate(sorted_users, start=1):
        user_name = data.get("name", f"Foydalanuvchi {user_id}")
        rating = data["rating"]
        rank = get_rank(rating)  # Unvonni aniqlash
        users_list += f"{idx}. {user_name} - {rating:.2f} ball  ({rank})\n"

    await message.answer(users_list, parse_mode="Markdown")


@dp.message(Command("register"))
async def register_handler(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)

    if user_id in user_profiles and user_profiles[user_id]["school"] is not None:
        await message.answer("⛔ Siz allaqachon ro‘yxatdan o‘tgansiz!\n"
                             "Agar ma'lumotlaringizni yangilashni xohlasangiz, admin bilan bog‘laning.")
        return

    await message.answer("👤 Iltimos, to‘liq ismingizni kiriting:")
    await state.set_state(RegisterState.full_name)

@dp.message(RegisterState.full_name)
async def process_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("🏫 Endi maktabingiz nomini yoki raqamini kiriting:")
    await state.set_state(RegisterState.school)

@dp.message(RegisterState.school)
async def process_school(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    data = await state.get_data()

    user_profiles[user_id] = {
        "id": user_id,
        "name": data["full_name"],
        "school": message.text,
        "rating": 0,
        "contests_participated": 0
    }
    save_json(USER_PROFILES_FILE, user_profiles)

    await message.answer(f"✅ Ro‘yxatdan o‘tish tugallandi!\n\n"
                         f"👤 *Ism-Familiya:* {data['full_name']}\n"
                         f"🏫 *Maktab:* {message.text}",
                         parse_mode="Markdown")

    await state.clear() ## end

class ContestState(StatesGroup): ## add_contest
    name = State()
    grade = State()
    subject = State()
    start_time = State()
    end_time = State()

@dp.message(Command("add_contest"))
async def add_contest_handler(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Siz admin emassiz!")
        return

    await message.answer("📌 Contest nomini kiriting:")
    await state.set_state(ContestState.name)

@dp.message(ContestState.name)
async def contest_name_handler(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📚 Contest qaysi sinf uchun ekanligini kiriting (masalan, 10-sinf):")
    await state.set_state(ContestState.grade)

@dp.message(ContestState.grade)
async def contest_grade_handler(message: Message, state: FSMContext):
    await state.update_data(grade=message.text)
    await message.answer("📖 Contest fani nomini kiriting (masalan, Matematika):")
    await state.set_state(ContestState.subject)

@dp.message(ContestState.subject)
async def contest_subject_handler(message: Message, state: FSMContext):
    await state.update_data(subject=message.text)
    await message.answer("⏰ Contest boshlanish vaqtini kiriting (Format: YYYY-MM-DD HH:MM):")
    await state.set_state(ContestState.start_time)

@dp.message(ContestState.subject)
async def contest_subject_handler(message: Message, state: FSMContext):
    await state.update_data(subject=message.text)
    await message.answer("⏰ Contest boshlanish vaqtini kiriting (Format: YYYY-MM-DD HH:MM):")
    await state.set_state(ContestState.start_time)

@dp.message(ContestState.start_time)
async def contest_start_time_handler(message: Message, state: FSMContext):
    try:
        start_time = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
        await state.update_data(start_time=message.text)  # Foydalanuvchi kiritgan vaqti string shaklda saqlanadi

        await message.answer("⏳ Contest tugash vaqtini kiriting (Format: YYYY-MM-DD HH:MM):")
        await state.set_state(ContestState.end_time)
    except ValueError:
        await message.answer("❌ Xato! Iltimos, to‘g‘ri formatda yozing: YYYY-MM-DD HH:MM")

@dp.message(ContestState.end_time)
async def contest_end_time_handler(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        end_time = datetime.strptime(message.text, "%Y-%m-%d %H:%M")

        contest_id = str(random.randint(1000, 99999999))
        contests[contest_id] = {
            "id": contest_id,
            "name": data["name"],
            "grade": data["grade"],
            "subject": data["subject"],
            "start_time": data["start_time"],  # Oldindan saqlangan boshlanish vaqtini ishlatamiz
            "end_time": message.text  # Tugash vaqtini saqlaymiz
        }
        save_json(CONTESTS_FILE, contests)

        await message.answer(f"✅ Contest qo‘shildi!\n\n"
                             f" ID: {contest_id}\n"
                             f"📌 Nomi: {data['name']}\n"
                             f"🎓 Sinf: {data['grade']}\n"
                             f"📖 Fan: {data['subject']}\n"
                             f"🕒 Boshlanish vaqti: {data['start_time']} (UTC +5)\n"
                             f"⏳ Tugash vaqti: {message.text} (UTC +5)",
                             parse_mode="HTML")

        await state.clear()
    except ValueError:
        await message.answer("❌ Xato! Iltimos, to‘g‘ri formatda yozing: YYYY-MM-DD HH:MM")

#########################

ANSWERS_FILE = "answers.json"
answers = load_json(ANSWERS_FILE)

@dp.message(Command("add_answers"))
async def start_adding_answers(message: types.Message, state: FSMContext):
    """ Foydalanuvchidan contest ID ni so‘rash """
    contests_list = "\n".join([f"{key}: {value['name']}" for key, value in contests.items()])
    
    await message.answer(f"📌 To‘g‘ri javoblarni yuklash uchun contest ID sini kiriting:\n\n{contests_list}")
    await state.set_state(AnswerState.contest_id)

@dp.message(AnswerState.answers)
async def process_answers(message: types.Message, state: FSMContext):
    """ Foydalanuvchi kiritgan javoblarni saqlash """
    data = await state.get_data()
    contest_id = data["contest_id"]
    user_answers = message.text.strip()

    # Javoblarni saqlash
    answers[contest_id] = user_answers
    save_json(ANSWERS_FILE, answers)

    await message.answer(f"✅ {contest_id} ID-li contest uchun to‘g‘ri javoblar saqlandi!")
    await state.clear()

@dp.message(Command("profile"))
async def profile_handler(message: Message):
    # user_profiles.json ni qayta yuklash
    try:
        with open("user_profiles.json", "r") as file:
            user_profiles = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        user_profiles = {}

    user_id = str(message.from_user.id)

    if user_id in user_profiles:
        user_data = user_profiles[user_id]

        # Reyting bo‘yicha foydalanuvchilarning o‘rnini aniqlash
        sorted_users = sorted(user_profiles.items(), key=lambda x: x[1]["rating"], reverse=True)
        user_rank = next((idx + 1 for idx, (u_id, _) in enumerate(sorted_users) if u_id == user_id), "Noma'lum")

        # 🏆 Foydalanuvchi darajasini aniqlash
        def get_rank(rating):
            if rating >= 2800:
                return "🟤 Legendary Grandmaster"
            elif rating >= 2200:
                return "⚫ Grandmaster"
            elif rating >= 1600:
                return "🔴 Master"
            elif rating >= 1000:
                return "🟠 Candidate Master"
            elif rating >= 600:
                return "🟣 Expert"
            elif rating >= 300:
                return "🔵 Specialist"
            elif rating >= 100:
                return "🟡 Pupil"
            else:
                return "🚼 Newbie"

        rank_title = get_rank(user_data['rating'])

        profile_text = (f"📌 *Sizning Profilingiz:*\n\n"
                        f"🆔 *ID:* {user_data['id']}\n"
                        f"👤 *Ism:* {user_data['name']}\n"
                        f"🏫 *Maktab:* {user_data.get('school', 'Kiritilmagan')}\n"
                        f"⭐ *Umumiy Reyting:* {user_data['rating']}  (#{user_rank})\n"
                        f"🏆 *Qatnashgan Contestlar:* {user_data['contests_participated']}\n\n"
                        f"📊 *Daraja:* {rank_title}")  # 👈 Yangi darajalar kiritildi
        await message.answer(profile_text, parse_mode="Markdown")
    else:
        await message.answer("🚫 Siz ro‘yxatdan o‘tmagansiz. Iltimos, /register buyrug‘ini bering.")

@dp.message(lambda message: message.text.lower() == "profile")
async def profile_button_handler(message: Message):
    await profile_handler(message)


@dp.message(lambda message: message.text.lower() == "register")
async def register_button_handler(message: Message, state: FSMContext):
    await register_handler(message, state)

async def main():
    print("Bot ishga tushdi ✅")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 
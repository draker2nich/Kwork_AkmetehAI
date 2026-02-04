from aiogram.fsm.state import StatesGroup, State


class MassSend(StatesGroup):
    msg = State()
    confirmation = State()


class AdminState(StatesGroup):
    waiting_for_category_name = State()
    waiting_for_category_prompt = State()
    waiting_for_new_prompt = State()
    waiting_for_new_category_name = State()

    waiting_for_item_name = State()
    waiting_for_item_content = State()
    waiting_for_new_item_name = State()
    waiting_for_new_item_desc = State()
    waiting_for_new_item_file = State()
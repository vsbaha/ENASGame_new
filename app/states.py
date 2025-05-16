from aiogram.fsm.state import StatesGroup, State

class CreateTournament(StatesGroup):
    SELECT_GAME = State()
    NAME = State()
    LOGO = State()
    START_DATE = State()
    DESCRIPTION = State()
    REGULATIONS = State()
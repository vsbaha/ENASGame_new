from aiogram.fsm.state import StatesGroup, State

class CreateTournament(StatesGroup):
    SELECT_GAME = State()
    SELECT_FORMAT = State()
    NAME = State()
    LOGO = State()
    START_DATE = State()
    DESCRIPTION = State()
    REGULATIONS = State()
    
class RegisterTeam(StatesGroup):
    SELECT_TOURNAMENT = State()
    TEAM_NAME = State()
    TEAM_LOGO = State()
    ADD_PLAYERS = State()
    CONFIRMATION = State()
    
class AdminActions(StatesGroup):
    WAITING_ADMIN_USERNAME = State()  # Замените WAITING_ADMIN_ID на это
    
class EditTeam(StatesGroup):
    NAME = State()
    LOGO = State()
    PLAYERS = State()
    CHOICE = State()
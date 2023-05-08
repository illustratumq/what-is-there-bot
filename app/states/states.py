from app.states.base import *


class PostSG(StatesGroup):
    Title = State()
    About = State()
    Price = State()
    Media = State()
    Confirm = State()


class ParticipateSG(StatesGroup):
    Comment = State()


class MarkerSG(StatesGroup):
    Add = State()
    Delete = State()


class CommentSG(StatesGroup):
    Input = State()
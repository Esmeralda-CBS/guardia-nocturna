from fastapi.templating import Jinja2Templates
from guardia.database import es_date

templates = Jinja2Templates(directory="templates")
templates.env.filters["es_date"] = es_date

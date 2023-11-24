import asyncio

from django.core import serializers
from django.http import HttpResponse, JsonResponse
from kinopoisk_dev import KinopoiskDev, PossValField, MovieParams, MovieField
from .models import Card, Type
from .tokens import TOKENS
from asgiref.sync import sync_to_async

kp = KinopoiskDev(token=TOKENS['kinopoisk'])


async def get_movies_async(type):
    params = [
        MovieParams(keys=MovieField.PAGE, value=3),
        MovieParams(keys=MovieField.LIMIT, value=1000),
        MovieParams(keys=MovieField.TYPE, value=type),
    ]

    item = await kp.afind_many_movie(params=params)
    return item

async def index(request):
    print('1')
    type = await sync_to_async(Type.objects.get, thread_sensitive=True)(pk=1)
    print('1.1')

    movies = await get_movies_async(type.name)
    for movie in movies.docs:
        print('3')
        cards = await sync_to_async(Card.objects.filter, thread_sensitive=True)(kp_id=movie.id)
        len_cards = await sync_to_async(len, thread_sensitive=True)(cards)
        if len_cards == 0:
            card = Card(name=movie.name,
                        filename=movie.poster.url or "",
                        description=movie.shortDescription,
                        rate=movie.rating.kp,
                        year=movie.year,
                        kp_id=movie.id,
                        )
            await card.asave()
            print('4')
            await sync_to_async(card.types.add, thread_sensitive=True)(type)
            print('5')
    print('gfdg12301250-09-')

    return HttpResponse("OK")

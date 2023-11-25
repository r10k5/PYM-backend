import asyncio

from django.core import serializers
from django.http import HttpResponse, JsonResponse
from kinopoisk_dev import KinopoiskDev, PossValField, MovieParams, MovieField
from .models import Card, Type, Genre
from .tokens import TOKENS
from asgiref.sync import sync_to_async

kp = KinopoiskDev(token=TOKENS['kinopoisk'])


async def get_movies_async(type):
    params = [
        MovieParams(keys=MovieField.PAGE, value=1),
        MovieParams(keys=MovieField.LIMIT, value=250),
        MovieParams(keys=MovieField.TYPE, value=type),
    ]

    item = await kp.afind_many_movie(params=params)
    return item

async def write_kp(request):
    type = await sync_to_async(Type.objects.get, thread_sensitive=True)(pk=1)

    movies = await get_movies_async(type.name)
    for movie in movies.docs:
        cards = await sync_to_async(Card.objects.filter, thread_sensitive=True)(kp_id=movie.id)
        len_cards = await sync_to_async(len, thread_sensitive=True)(cards)
        if len_cards == 0:
            card = Card(name=movie.name,
                        filename=movie.poster.url or "",
                        description=movie.shortDescription,
                        rate=movie.rating.kp,
                        year=movie.year,
                        kp_id=movie.id,
                        duration_all=movie.movieLength or 0,
                        )
            await card.asave()
            await sync_to_async(card.types.add, thread_sensitive=True)(type)

            genres = Genre.objects.all()
            filtered_genres = []

            for genre in movie.genres:
                filtered = await sync_to_async(filter)(lambda g: g.name == genre.name, genres)
                [g] = await sync_to_async(list)(filtered)
                await sync_to_async(filtered_genres.append)(g)
            await sync_to_async(card.genres.add, thread_sensitive=True)(*filtered_genres)

    return HttpResponse('OK')

def index(request):
    result = []
    cards = Card.objects.filter(types__in=[1])

    for card in cards:
        genres = list(map(lambda genre: genre.name, card.genres.all()))
        types = list(map(lambda type: type.name, card.types.all()))

        result.append({
            'id': card.id,
            'name': card.name,
            'filename': card.filename,
            'description': card.description,
            'rate': card.rate,
            'genres': genres,
            'types': types,
            'year': card.year,
            'duration_all': card.duration_all,
            'duration_series': card.duration_series,
            'count_series': card.count_series,
        })

    return JsonResponse(result, safe=False)

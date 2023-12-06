import asyncio

from django.core import serializers
from django.http import HttpResponse, JsonResponse
from kinopoisk_dev import KinopoiskDev, PossValField, MovieParams, MovieField
from .models import Card, Type, Genre
from .tokens import TOKENS, SALT
from asgiref.sync import sync_to_async
from .redis import redis_client
import json
from django.core.exceptions import ObjectDoesNotExist
import datetime
import hashlib

kp = KinopoiskDev(token=TOKENS['kinopoisk'])


async def get_movies_async(type, page):
    params = [
        MovieParams(keys=MovieField.PAGE, value=page),
        MovieParams(keys=MovieField.LIMIT, value=260),
        MovieParams(keys=MovieField.TYPE, value=type),
    ]

    item = await kp.afind_many_movie(params=params)
    return item

async def write_kp(request):
    page = await sync_to_async(request.GET.get)('page', '0')
    page = await sync_to_async(int)(page)
    type_id = await sync_to_async(request.GET.get)('type', '1')
    type_id = await sync_to_async(int)(type_id)
    type = await sync_to_async(Type.objects.get, thread_sensitive=True)(pk=type_id)

    movies = await get_movies_async(type.name, page)
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
                g = await sync_to_async(list)(filtered)
                if await sync_to_async(len)(g) != 0:
                    await sync_to_async(filtered_genres.append)(*g)
            await sync_to_async(card.genres.add, thread_sensitive=True)(*filtered_genres)

    return HttpResponse('OK')

async def check_to_session(request, uid):
    session = await redis_client.get(uid)

    if session is None:
        return HttpResponse('404')
    return HttpResponse('OK')

async def connect_to_session(request, uid):
    session = await redis_client.get(uid)

    if session is None:
        return HttpResponse('404')

    body_unicode = request.body.decode('utf-8')
    body_data = json.loads(body_unicode)

    if not body_data.has_key('name'):
        if session['creator_name'] == body_data['name']:
            return JsonResponse({
                'name': session['creator_name'],
                'is_creator': True,
            }, safe=False)

        for name in session['guest_names']:
            if name == body_data['name']:
                return JsonResponse({
                    'name': name,
                    'is_creator': False,
                }, safe=False)

        if session['limit'] == len(session['guest_names']):
            return JsonResponse({
                    'error': 'Достигнут лимит участников'
                }, safe=False)
        session['guest_names'].append(body_data['name'])

        redis_client.hset(uid, session)
        return JsonResponse({
                    'name': body_data['name'],
                    'is_creator': False,
                }, safe=False)

def create_session(request):
    body_unicode = request.body.decode('utf-8')
    body_data = json.loads(body_unicode)
    if not (body_data.has_key('type')
            and body_data.has_key('genre')
            and body_data.has_key('name')
            and body_data.has_key('limit')):
        return HttpResponse('error')
    type = int(body_data['type'])
    genre = int(body_data['genre'])
    name = body_data['name']
    limit = int(body_data['limit'])

    try:
        type = Type.objects.get(pk=type)
        genre = Genre.objects.get(pk=genre)
        session_time = datetime.datetime.now().timestamp()

        uid = f"{type.name}-{genre.name}-{session_time}-{SALT}"
        uid = hashlib.sha256(uid).hexdigest()
        redis_client.hset(uid, maping={
            'creator_name': name,
            'guest_names': [],
            'genre': genre,
            'type': type,
            'limit': limit,
            'uid': uid,
            'history': [],
            'status': False,
            'result': [],
        })

        return JsonResponse({
                    'uid': uid,
                }, safe=False)

    except ObjectDoesNotExist:
        return HttpResponse('Type or genre does not exist')



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

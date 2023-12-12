from django.http import HttpResponse, JsonResponse
from kinopoisk_dev import KinopoiskDev, MovieParams, MovieField
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


def check_to_session(request, uid):
    session = redis_client.get(uid)

    if session is None:
        return HttpResponse('404')

    session = json.loads(session)

    if session['limit'] == len(session['guest_names']):
        return HttpResponse('Достигнут лимит участников')

    return HttpResponse('OK')


def connect_to_session(request, uid):
    session = redis_client.get(uid)

    if session is None:
        return HttpResponse('404')

    session = json.loads(session)

    body_unicode = request.body.decode('utf-8')
    body_data = json.loads(body_unicode)
    if 'name' in body_data:
        if session['creator_name'] == body_data['name']:
            return JsonResponse(session, safe=False)

        for name in session['guest_names']:
            if name == body_data['name']:
                return JsonResponse(session, safe=False)

        if session['status'] == 'finished':
            return JsonResponse({
                'error': 'Сессия уже завершилась'
            }, safe=False)

        if session['limit'] == len(session['guest_names']):
            return JsonResponse({
                'error': 'Достигнут лимит участников'
            }, safe=False)

        session['guest_names'].append(body_data['name'])
        redis_client.set(uid, json.dumps(session))
        return JsonResponse(session, safe=False)

    return JsonResponse({
        'error': 'Имя пользователя не указано'
    }, safe=False)


def start_session(request, uid):
    session = redis_client.get(uid)
    body_unicode = request.body.decode('utf-8')
    body_data = json.loads(body_unicode)

    if 'name' not in body_data:
        return JsonResponse({
            'error': '400'
        }, safe=False)

    if session is None:
        return JsonResponse({
            'error': '404'
        }, safe=False)

    name = body_data['name']
    session = json.loads(session)

    if session['creator_name'] != name:
        return JsonResponse({
            'error': '403'
        }, safe=False)

    session['status'] = 'started'

    redis_client.set(uid, json.dumps(session))

    return JsonResponse(session, safe=False)


def get_session(request, uid):
    session = redis_client.get(uid)
    body_unicode = request.body.decode('utf-8')
    body_data = json.loads(body_unicode)

    if 'name' not in body_data:
        return JsonResponse({
            'error': '400'
        }, safe=False)

    if session is None:
        return JsonResponse({
            'error': '404'
        }, safe=False)

    name = body_data['name']
    session = json.loads(session)

    if session['status'] == 'finished':
        return JsonResponse({
            'error': '404'
        }, safe=False)

    if session['creator_name'] == name or name in session['guest_names']:
        return JsonResponse(session, safe=False)

    return JsonResponse({
        'error': '403'
    }, safe=False)


def check_results(session):
    concreate_result = []
    results = {}
    for record in session['history']:
        result_id = str(record['card']['id'])
        if str(record['card']['id']) in results:
            if record['isLike']:
                results[result_id] += 1
        else:
            results[result_id] = 0
            if record['isLike']:
                results[result_id] += 1

        if results[result_id] == session['limit']:
            concreate_result.append({
                'card': record['card'],
                'likeCount': results[result_id]
            })

    return concreate_result


def like_card(request, uid):
    body_unicode = request.body.decode('utf-8')
    body_data = json.loads(body_unicode)

    if ('name' not in body_data
            and 'value' not in body_data
            and 'card_id' not in body_data):
        return JsonResponse({
            'error': '400',
        }, safe=False)

    session = redis_client.get(uid)

    if session is None:
        return JsonResponse({
            'error': '404',
        }, safe=False)

    name = body_data['name']
    session = json.loads(session)
    [card] = list(filter(lambda card: card['id'] == body_data['card_id'], session['cards']))

    session['history'].append({
        'card': card,
        'user': name,
        'isLike': body_data['value']
    })

    session['result'] = check_results(session)

    redis_client.set(uid, json.dumps(session))

    return JsonResponse(session, safe=False)


def create_session(request):
    body_unicode = request.body.decode('utf-8')
    body_data = json.loads(body_unicode)

    if ('type' not in body_data
            and 'genre' not in body_data
            and 'name' not in body_data
            and 'limit' not in body_data):
        return HttpResponse('error')

    type = int(body_data['type'])
    genre = int(body_data['genre'])
    name = body_data['name']
    limit = int(body_data['limit'])

    try:
        type_db = Type.objects.get(pk=type)
        genre_db = Genre.objects.get(pk=genre)
        cards = Card.objects.filter(genres=genre_db.id, types=type_db.id).order_by('?')[:30]
        mapped_cards = []
        session_time = datetime.datetime.now().timestamp()

        for card in cards:
            genres = list(map(lambda genre_orm: genre_orm.name, card.genres.all()))
            types = list(map(lambda type_orm: type_orm.name, card.types.all()))

            mapped_cards.append({
                'id': card.id,
                'name': card.name,
                'filename': card.filename,
                'description': card.description,
                'rate': float(card.rate),
                'genres': genres,
                'types': types,
                'year': card.year,
                'duration_all': card.duration_all,
                'duration_series': card.duration_series,
                'count_series': card.count_series,
            })

        uid = f"{type_db.name}-{genre_db.name}-{session_time}-{SALT}"
        uid = hashlib.sha256(uid.encode('utf-8')).hexdigest()

        session_obj = {
            'creator_name': name,
            'guest_names': [],
            'genre': genre_db.id,
            'type': type_db.id,
            'limit': limit,
            'uid': uid,
            'history': [],
            'status': 'pending',
            'result': [],
            'cards': mapped_cards,
        }
        print(session_obj)
        redis_client.set(uid, json.dumps(session_obj))

        return JsonResponse(session_obj, safe=False)

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

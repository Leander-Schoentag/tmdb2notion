import os
import requests
from configparser import ConfigParser


def check_valid_tmdb_id(tmdb_id):
    if not tmdb_id.startswith(('movie/', 'tv/')) or not tmdb_id.split('/')[1].isdigit():
        raise SystemExit(f"Error: TMDB ID '{tmdb_id}' is invalid.")


def get_user_database_id():
    database = ConfigParser()
    database.read(os.path.join(os.path.dirname(__file__), 'database.ini'))

    section = 'id'

    if not database.has_section(section):
        raise SystemExit(
            "Error: The [id] section is missing in 'database.ini'")

    database_ids = dict(database.items(section))

    if not database_ids:
        raise SystemExit("Error: Missing notion database_id in 'database.ini'")

    if len(database_ids) == 1:
        selected_name = list(database_ids.keys())[0]
    else:
        for i, name in enumerate(database_ids, start=1):
            print(f"{i} - {name}")

        user_selected = int(
            input("Select your notion database_id with the corresponding number: "))
        selected_name = list(database_ids.keys())[user_selected - 1]
        selected_id = database_ids[selected_name]

    print(f"Selected notion database_id: {selected_name} -> {selected_id}")
    return selected_id


def get_user_token():
    config = ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))

    return {
        'tmdb_access_token_auth': config.get('themoviedb', 'tmdb_access_token_auth'),
        'language_param': config.get('themoviedb', 'language_param'),
        'notion_integration_secret': config.get('notion', 'notion_integration_secret')
    }


def get_tmdb_api_url(tmdb_id):
    media_type = tmdb_id.split('/')[0]
    tmdb_id = tmdb_id.split('/')[1]
    BASE_URL = 'https://api.themoviedb.org/3/'
    language_param = get_user_token()['language_param']

    return {
        'media_type': media_type,
        'details': f"{BASE_URL}{media_type}/{tmdb_id}?language={language_param}",
        'credits': f"{BASE_URL}{media_type}/{tmdb_id}/credits?language={language_param}",
        'external_ids': f"{BASE_URL}{media_type}/{tmdb_id}/external_ids",
        'videos': f"{BASE_URL}{media_type}/{tmdb_id}/videos?language={language_param}"
    }


def get_tmdb_endpoint_request(url):
    headers = {
        'Authorization': f"Bearer {get_user_token()['tmdb_access_token_auth']}"}
    response = requests.get(url, headers=headers)
    return response.json()


def r_details(tmdb_id):
    return get_tmdb_endpoint_request(get_tmdb_api_url(tmdb_id)['details'])


def r_credits(tmdb_id):
    return get_tmdb_endpoint_request(get_tmdb_api_url(tmdb_id)['credits'])


def r_external_ids(tmdb_id):
    return get_tmdb_endpoint_request(get_tmdb_api_url(tmdb_id)['external_ids'])


def r_videos(tmdb_id):
    return get_tmdb_endpoint_request(get_tmdb_api_url(tmdb_id)['videos'])


def cover(tmdb_id):
    return f"https://image.tmdb.org/t/p/original{r_details(tmdb_id)['backdrop_path']}"


def icon(tmdb_id):
    return f"https://image.tmdb.org/t/p/original{r_details(tmdb_id)['poster_path']}"


def title(tmdb_id):
    return r_details(tmdb_id)['title'] if get_tmdb_api_url(tmdb_id)['media_type'] == "movie" else r_details(tmdb_id)['name']


def release(tmdb_id):
    details = r_details(tmdb_id)
    if get_tmdb_api_url(tmdb_id)['media_type'] == "movie":
        return details['release_date'][:4]
    else:
        first_air = details['first_air_date'][:4]
        last_air = details['last_air_date'][:4]
        return f"{first_air} - {last_air}"


def genres(tmdb_id):
    return [{'name': genre['name']} for genre in r_details(tmdb_id)['genres']]


def seasons(tmdb_id):
    if get_tmdb_api_url(tmdb_id)['media_type'] == "tv":
        return str(r_details(tmdb_id)["number_of_seasons"])


def episodes(tmdb_id):
    if get_tmdb_api_url(tmdb_id)['media_type'] == "tv":
        return str(r_details(tmdb_id)["number_of_episodes"])


def overview(tmdb_id):
    return r_details(tmdb_id)['overview']


def directors(tmdb_id):
    if get_tmdb_api_url(tmdb_id)['media_type'] == "movie":
        return "\n".join([crew_member["name"] for crew_member in r_credits(tmdb_id)["crew"] if crew_member["job"] == "Director"])
    else:
        return "\n".join([director["name"] for director in r_details(tmdb_id)["created_by"]])


def actors(tmdb_id):
    return "\n".join([f"{actor['name']} - {actor['character']}" for actor in r_credits(tmdb_id)["cast"][:3]])


def tmdb_to_imdb(tmdb_id):
    return r_external_ids(tmdb_id)['imdb_id']


def trailer(tmdb_id):
    video_id = r_videos(tmdb_id)["results"]
    key = video_id[0]['key'] if video_id else "Y7dpJ0oseIA"
    return f"https://www.youtube.com/watch?v={key}"


def create_a_notion_page(cover, icon, title, release, seasons, episodes, genres, overview, directors, actors, imdb_id, tmdb_id, trailer):
    url = 'https://api.notion.com/v1/pages'

    headers = {
        "Authorization": f"Bearer {get_user_token()['notion_integration_secret']}",
        "Notion-Version": "2022-06-28",
        "content-type": "application/json"
    }

    payload = {
        "cover": {"external": {"url": cover}},
        "icon": {"external": {"url": icon}},
        "parent": {"database_id": get_user_database_id()},
        "properties": {
            "Title": {"title": [{"text": {"content": title}}]},
            "Release": {"rich_text": [{"text": {"content": release}}]},
            "Seasons": {"rich_text": [{"text": {"content": seasons}}]},
            "Episodes": {"rich_text": [{"text": {"content": episodes}}]},
            "Genre": {"multi_select": genres},
            "Plot": {"rich_text": [{"text": {"content": overview}}]},
            "Director": {"rich_text": [{"text": {"content": directors}}]},
            "Actors": {"rich_text": [{"text": {"content": actors}}]}
        },
        "children": [
            {"paragraph": {"rich_text": [{"type": "text", "text": {
                "content": f"https://www.imdb.com/title/{imdb_id}", "link": {"url": f"https://www.imdb.com/title/{imdb_id}"}}}]}},
            {"paragraph": {"rich_text": [{"type": "text", "text": {
                "content": f"https://www.themoviedb.org/{tmdb_id}", "link": {"url": f"https://www.themoviedb.org/{tmdb_id}"}}}]}},
            {"video": {"external": {"url": trailer}}}
        ]
    }

    if get_tmdb_api_url(tmdb_id)['media_type'] == "movie":
        del payload["properties"]["Seasons"], payload["properties"]["Episodes"]

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        raise SystemExit(response.text)

    print(response.status_code)
    return response


def main():
    tmdb_id = input('Please insert the TMDB-ID here: ')  # tv/1396 or movie/603
    check_valid_tmdb_id(tmdb_id)

    create_a_notion_page(cover(tmdb_id), icon(tmdb_id), title(tmdb_id), release(tmdb_id), seasons(tmdb_id), episodes(tmdb_id), genres(tmdb_id),
                         overview(tmdb_id), directors(tmdb_id), actors(tmdb_id), tmdb_to_imdb(tmdb_id), tmdb_id, trailer(tmdb_id))

    print(title(tmdb_id))


if __name__ == '__main__':
    main()
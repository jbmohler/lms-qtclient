import rtxsite
import client


def delete_personas_by_tag(session, tagname):
    mycli = session.std_client()

    tags = mycli.get('api/tags/list')

    tag_id = [tag.id for tag in tags.main_table().rows if tag.name == tagname][0]

    personas = mycli.get('api/personas/list', tag_id=tag_id)

    for persona in personas.main_table().rows:
        print('delete -- ', persona)
        mycli.delete(f'api/persona/{persona.id}')


if __name__ == '__main__':
    session = client.auto_session()

    try:
        delete_personas_by_tag(session, "Students")
    finally:
        session.close()

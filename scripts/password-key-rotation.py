import rtxsite
import client
import localconfig


def password_key_rotation(session):
    mycli = session.std_client()

    bits = mycli.get("api/personas/all-bits", bit_type="urls")

    for rec in bits.named_table("contacts").rows:
        passbit = mycli.get(
            "api/persona/{}/bit/{}", rec.persona_id, rec.id, bit_type="urls"
        )

        bittable = passbit.named_table("bit")

        mycli.put(
            "api/persona/{}/bit/{}",
            rec.persona_id,
            rec.id,
            bit_type="urls",
            files={"bit": bittable.as_http_post_file(inclusions=["password"])},
        )


if __name__ == "__main__":
    localconfig.set_identity()
    session = client.auto_session()

    try:
        password_key_rotation(session)
    finally:
        session.close()

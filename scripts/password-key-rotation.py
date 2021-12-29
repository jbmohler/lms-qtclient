import rtxsite
import client
import localconfig


def password_key_rotation(session):
    mycli = session.std_client()

    bits = mycli.get("api/personas/all-bits", bit_type="urls")

    def get_password(rec):
        passbit1 = mycli.get(
            "api/persona/{}/bit/{}", rec.persona_id, rec.id, bit_type="urls"
        )

        return passbit1.named_table("bit").rows[0].password

    for rec in bits.named_table("contacts").rows:
        pass1 = get_password(rec)

        mycli.put("api/persona/{}/bit/{}/rotate", rec.persona_id, rec.id)

        pass2 = get_password(rec)

        assert pass1 == pass2, "Key rotation failed"


if __name__ == "__main__":
    localconfig.set_identity()
    session = client.auto_session()

    try:
        password_key_rotation(session)
    finally:
        session.close()

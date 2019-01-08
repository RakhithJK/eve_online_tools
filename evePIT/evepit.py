import configparser
import json
import traceback
from esipy import EsiApp, EsiClient, EsiSecurity

# setup configuration
config = configparser.RawConfigParser()
config.read('config.conf')
client_id = config.get('esi', 'client_id')
secret_key = config.get('esi', 'secret_key')
refresh_tokens = json.loads(config.get('esi', 'refresh_tokens'))

# setup ESI objects
print("Building EsiApp app...")
app = EsiApp().get_latest_swagger
security = EsiSecurity(redirect_uri='http://localhost:8888', client_id=client_id, secret_key=secret_key)
client = EsiClient(retry_requests=True, headers={'User-Agent': 'https://github.com/gradiuscypher/eve_online_tools'},
                   security=security)


class EvePit:
    def __init__(self):
        self.active_character = None
        self.active_character_id = None

    def set_active_character(self, refresh_token):
        """
        Set the active character's authentication via their refresh token
        :param refresh_token:
        :return:
        """
        # setup authentication for provided refresh token
        security.update_token({'access_token': '', 'expires_in': -1, 'refresh_token': refresh_token})
        security.refresh()
        self.active_character = security.verify()
        self.active_character_id = self.active_character['sub'].split(':')[-1]

    def get_character_planets(self):
        """
        Gets all planets related to PI for the character
        :param refresh_token: the refresh token of the character auth
        :return:
        """
        if not self.active_character:
            print("Please set an active character first.")

        else:
            operation = app.op['get_characters_character_id_planets'](character_id=self.active_character_id)

            try:
                planets = client.request(operation)

                if planets.status == 200:
                    return planets.data
                else:
                    print(f"[Code {planets.status}]: {planets.raw}")
                    return []
            except:
                print(traceback.format_exc())

    def get_character_pi_setup(self):
        """
        Return a list of products and their counts on a planet.
        :param planet_id:
        :return:
        """
        planet_list = self.get_character_planets()
        planet_products = []

        if len(planet_list) > 0:
            for planet in planet_list:
                try:
                    operation = app.op['get_characters_character_id_planets_planet_id'](character_id=self.active_character_id, planet_id=planet['planet_id'])
                    pi_setup = client.request(operation)

                    if pi_setup.status == 200:
                        planet_products.append({'planet': planet, 'products': pi_setup.data})
                    else:
                        print(f"[Code {pi_setup.status}]: {pi_setup.raw}")

                except:
                    print(traceback.format_exc())

        return planet_products

    def generate_pi_report(self):
        pi_list = self.get_character_pi_setup()
        print(f"=== {self.active_character['name']} ===")

        if len(pi_list) > 0:
            for pi_setup in pi_list:
                try:
                    planet_data = client.request(app.op['get_universe_planets_planet_id'](planet_id=pi_setup['planet']['planet_id'])).data
                    planet_name = planet_data['name']
                    planet_type = pi_setup['planet']['planet_type']

                    print(f"{planet_name} ({planet_type}) [@{pi_setup['planet']['last_update'].to_json()}]")

                    for pin in pi_setup['products']['pins']:
                        if 'contents' in pin.keys() and 'schematic_id' not in pin.keys():
                            pin_data = client.request(app.op['get_universe_types_type_id'](type_id=pin['type_id'])).data
                            pin_name = pin_data['name']
                            print(f"[{pin_name}]")

                            for product in pin['contents']:
                                product_name = client.request(app.op['get_universe_types_type_id'](type_id=product['type_id'])).data['name']
                                print(f"  [+] {product_name}: {product['amount']}")

                    print()

                except:
                    print(traceback.format_exc())

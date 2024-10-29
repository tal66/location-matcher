import hashlib
import random
from typing import List
import logging

import numpy as np
import requests
from geopy.distance import geodesic
from scipy.special import lambertw

from client_display_map import create_map_html

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

SERVER_URL = "http://localhost:8000"


class LocationClient:
    def __init__(self, server_url=SERVER_URL, user_id=None, epsilon=1.1):
        self.server_url = server_url
        self.user_id = user_id
        self.epsilon = epsilon
        self.mechanism = Noise(epsilon=epsilon, rmax=3)
        self.access_token = self._get_access_token()
        self.headers = {"Content-Type": "application/json",
                        "accept": "application/json",
                        "Authorization": f"Bearer {self.access_token}"
                        }

    def _get_access_token(self, password: str = "secret"):
        url = f"{SERVER_URL}/login_for_access_token"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "username": self.user_id,
            "password": password
        }
        response = requests.post(url, headers=headers, data=data)

        if not response.ok:
            print(response.json())
            raise ValueError("Error getting access token")

        token = response.json()["access_token"]
        log.info(f"user '{self.user_id}' generated access token")
        return token

    def update_location(self, latitude: float, longitude: float):
        """send location update to server. adds noise to location before sending"""
        log.info(f"update location for user '{self.user_id}'")
        endpoint = f"{self.server_url}/locations"

        # add noise
        noisy_latitude, noisy_longitude = self._add_noise(latitude, longitude)

        # print distance
        print(f"noisy location: {noisy_latitude:.4f}, {noisy_longitude:.4f}, " +
              f"dist in km: {geodesic((latitude, longitude), (noisy_latitude, noisy_longitude)).kilometers:.2f}")

        data = {
            "user_id": self.user_id,
            "latitude": noisy_latitude,
            "longitude": noisy_longitude
        }

        try:
            response = requests.post(endpoint, json=data, headers=self.headers)
            if not response.ok:
                print(f"response: {response.json()}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error updating location: {e}")
            return None

    def _add_noise(self, latitude, longitude):
        log.info(f"add noise to location")
        return self.mechanism.add_noise(latitude, longitude)

    def get_nearby_users(self, max_distance_km: float = 6.0):
        """get users within specified distance (km)"""
        log.info(f"get nearby users for user '{self.user_id}'")
        endpoint = f"{self.server_url}/locations/nearby_users/?user_id={self.user_id}"
        params = {"max_distance": max_distance_km}
        try:
            response = requests.get(endpoint, params=params, headers=self.headers)
            if not response.ok:
                print(f"response: {response.json()}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting nearby users: {e}")
            return None


class Noise:
    def __init__(self, epsilon=1.0, grid_unit=0.0005, rmax=3):
        """
        variation of planar laplace mechanism, with parameter epsilon
        """
        self.epsilon = epsilon
        self.grid_unit = grid_unit
        self.rmax = rmax

    def _sample_polar(self):
        theta = np.random.uniform(0, 2 * np.pi)  # random angle in [0, 2π]
        p = np.random.uniform(0, 1)
        radius = -1 / self.epsilon * (lambertw((p - 1) / np.e, k=-1).real + 1)
        return radius, theta

    def add_noise(self, x, y):
        radius, theta = self._sample_polar()

        noise_x = radius * np.cos(theta) / 111.32
        noise_y = radius * np.sin(theta) / (111.32 * np.cos(np.radians(x)))

        # add noise to original coordinates
        noisy_x = x + noise_x
        noisy_y = y + noise_y

        # truncate to rmax
        distance = geodesic((noisy_x, noisy_y), (x, y)).kilometers
        if distance > self.rmax:
            scale_factor = self.rmax / distance * np.random.uniform(0.7, 1.0)
            # print(f"truncate distance: {distance}")
            noisy_x = x + (noisy_x - x) * scale_factor
            noisy_y = y + (noisy_y - y) * scale_factor

        # discretize to grid
        noisy_x = round(noisy_x / self.grid_unit) * self.grid_unit
        noisy_y = round(noisy_y / self.grid_unit) * self.grid_unit

        return noisy_x, noisy_y


class Util:
    @staticmethod
    def plot_distances(noisy_points, mechanism: Noise = None):
        import matplotlib.pyplot as plt
        true_location = (51.5007, -0.1246)

        # distances from each noisy point to the true location
        distances = [geodesic(true_location, noisy_point).kilometers for noisy_point in noisy_points]
        l = len(distances)
        # print(distances)

        # plot histogram of distances
        plt.figure(figsize=(10, 6))
        plt.hist(distances, bins=30, edgecolor='black', alpha=0.7)
        plt.xlabel("Distance from True Location (km)", fontsize=16)
        plt.ylabel("Frequency", fontsize=16)
        t = f"Distribution of Distances from True Location to Noisy Points"
        if mechanism:
            t += f"\nn={l:,}, ε={mechanism.epsilon}, rmax={mechanism.rmax} km"
        plt.title(t, fontsize=20)
        # plt.axvline(x=3, color='red', linestyle='--', label="rmax = 3 km")

        # average distance and median distance
        plt.axvline(x=float(np.mean(distances)), color='green', linestyle='--', label="Average Distance")
        plt.axvline(x=float(np.median(distances)), color='blue', linestyle='--', label="Median Distance")

        plt.legend()
        plt.show()

    @staticmethod
    def distribution_example(n=1000, epsilon=1.1, rmax=3):
        mechanism = Noise(epsilon=epsilon, rmax=rmax)
        big_ben_coords = (51.5007, -0.1246)

        points_x = []
        points_y = []
        max_dist_km = 0
        for i in range(n):
            noisy_x, noisy_y = mechanism.add_noise(*big_ben_coords)
            # print("Noisy location:", noisy_x, noisy_y)
            d = geodesic((noisy_x, noisy_y), (big_ben_coords[0], big_ben_coords[1])).kilometers
            max_dist_km = max(max_dist_km, d)
            points_x.append(noisy_x)
            points_y.append(noisy_y)
            # print(f"('p{i}', ST_SetSRID(ST_MakePoint({noisy_y}, {noisy_x}), 4326), NOW()),")

        avg_dist_km = np.mean([geodesic(big_ben_coords, (noisy_x, noisy_y)).kilometers for noisy_x, noisy_y
                               in zip(points_x, points_y)])
        median_dist_km = np.median([geodesic(big_ben_coords, (noisy_x, noisy_y)).kilometers for noisy_x, noisy_y
                                    in zip(points_x, points_y)])
        print(f"max distance in km: {max_dist_km}")
        print(f"avg distance in km: {avg_dist_km}")
        print(f"median distance in km: {median_dist_km}")
        Util.plot_distances(list(zip(points_x, points_y)), mechanism)


#######
p = int(
    'FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1'
    '29024E088A67CC74020BBEA63B139B22514A08798E3404DD'
    'EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245'
    'E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED'
    'EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D'
    'C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F'
    '83655D23DCA3AD961C62F356208552BB9ED529077096966D'
    '670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B'
    'E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9'
    'DE2BCBF6955817183995497CEA956AE515D2261898FA0510'
    '15728E5A8AACAA68FFFFFFFFFFFFFFFF', 16)


class PSIClient:
    def __init__(self, user_id, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.blinding_factor = random.randint(1, (p - 1) // 2 - 1)
        self.items = []
        self.user_id = user_id

    def _hash_and_blind(self, item: str) -> int:
        h = hashlib.sha256(item.encode()).digest()
        hi = int.from_bytes(h, 'big')
        return pow(hi, self.blinding_factor, p)

    def _blind(self, value: int) -> int:
        return pow(value, self.blinding_factor, p)


class InitiatorClient(PSIClient):
    def initiate(self, items: List[str]) -> str: # step 1
        self.items = items
        blinded_values = [self._hash_and_blind(x) for x in items]

        response = requests.post(
            f"{self.server_url}/psi/init",
            json={"blinded_values": blinded_values, "user_id": self.user_id}
        )

        if not response.ok:
            print(response.json())
            raise ValueError("Error initiating PSI")

        session_id = response.json()["session_id"]
        log.info(f"user '{self.user_id}' initiated PSI {session_id} with {len(items)} items (step 1)")
        return session_id

    def compute_intersection(self, session_id: str):
        log.info(f"'{self.user_id}' compute intersection for session {session_id} (step 3)")
        intersections = {}

        with requests.Session() as requests_session:
            response = requests_session.get(f"{self.server_url}/psi/{session_id}")
            if not response.ok:
                print(response.json())
                raise ValueError("Error computing intersection")
            if response.json()["status"] != 2:
                raise ValueError("Invalid session status (not 2)")

            response_values = response.json()["values"]

            for user, user_values in response_values.items():
                n = len(user_values) - len(self.items)
                bob_y_values = user_values[:n]
                bob_x_values = user_values[n:]

                alice_blinded_y = [self._blind(y) for y in bob_y_values]  # H(y)^ab

                # matches
                intersection = []
                for i, x in enumerate(self.items):
                    blinded_x = bob_x_values[i]
                    if blinded_x in alice_blinded_y:
                        intersection.append(x)

                intersections[user] = intersection

                # update server with intersection result
                requests_session.patch(
                    f"{self.server_url}/psi/{session_id}/intersection",
                    json={
                        "user_id": self.user_id,
                        "other_user_id": user,
                        "len_intersection": len(intersection)
                    }
                )

        return intersections


class JoinerClient(PSIClient):
    def join(self, session_id: str, items: List[str]) -> None: # step 2
        """ process initiator's values and sending response."""
        self.items = items
        log.info(f"user '{self.user_id}' join PSI {session_id} with {len(items)} items (step 2)")

        # get initiator's blinded values
        response = requests.get(f"{self.server_url}/psi/{session_id}")
        if not response.ok:
            print(response.json())
            raise ValueError("Error joining PSI")

        alice_values = response.json()["values"]

        # H(y)^b for self items
        blinded_y = [self._hash_and_blind(y) for y in items]

        # H(x)^ab for initiator's items
        double_blinded_x = [self._blind(x) for x in alice_values]

        # response
        response_values = blinded_y + double_blinded_x
        requests.post(
            f"{self.server_url}/psi/{session_id}/join",
            json={
                "session_id": session_id,
                "response_values": response_values,
                "user_id": self.user_id
            }
        )


if __name__ == "__main__":
    big_ben_coords = (51.5007, -0.1246)  # true location. user "big_ben"
    wembley_coords = (51.5580, -0.2765)  # true location. user "wembley"
    greenwich_coords = (51.4822, -0.0055)  # true location. user "greenwich"

    ### init user, update location, get nearby users
    coords = big_ben_coords
    user_id = "big_ben"
    client = LocationClient(user_id=user_id)
    # print(client.access_token)
    update_resp = client.update_location(*coords)  # this adds noise before sending to server
    nearby_users = client.get_nearby_users()
    print(f"\ntotal nearby_users: {len(nearby_users)}\n{nearby_users}")

    #### open html map in browser, displaying true and user noisy location
    import webbrowser
    true_location = coords
    noisy_location = update_resp["latitude"], update_resp["longitude"]
    fname = create_map_html(true_location, noisy_location)
    webbrowser.open("map.html")

    ##### psi
    other_user_id = nearby_users[0]["user_id"]  # closest user

    user_interests = ["sports", "books", "music", "movies", "programming", "nature"]
    other_user_interests = ["music", "travel", "movies", "nature", "food"]

    alice = InitiatorClient(user_id=user_id)
    session_id = alice.initiate(user_interests)

    bob = JoinerClient(user_id=other_user_id)
    bob.join(session_id, other_user_interests)  # future feature: joiner receives session_id from server/initiator

    intersections = alice.compute_intersection(session_id)
    print(f"intersections: {intersections}")

    # Util.distribution_example(1000, epsilon=1.1, rmax=3)

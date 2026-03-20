# script for scraping iNaturalist for images of a target species
# the script takes a species name as input via command line
# adapted from https://github.com/cypamigon/inat_downloader 

## set up ------------------------------------------------------------------

# libraries
import argparse
import csv
import requests
from requests.adapters import HTTPAdapter, Retry
import os
import datetime
import time

# query limits
MAX_QUERIES_PER_DAY = 9500 # max is 10,000
MAX_MEDIA_PER_HOUR = 4  # max is 5 gb
MAX_MEDIA_PER_DAY = 22 # max is 24 gb

# user query information
my_daily_queries = {"value": 0, "reset_time": datetime.datetime.now() + datetime.timedelta(hours=24)}
my_hourly_media = {"value": 0, "reset_time": datetime.datetime.now() + datetime.timedelta(hours=1)}
my_daily_media = {"value": 0, "reset_time": datetime.datetime.now() + datetime.timedelta(hours=24)}

# run info
max_observations_number = 0
current_observations_number = 0
current_images_number = 0
current_dataset_size = 0

# setting up a session that will retry on HTTP errors (429, 500, 502, 503, 504)
session = requests.Session()
retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))

## helper functions ------------------------------------------------------------------

def evaluate_query_rate():
    """wait if the daily query limit has been reached."""
    if my_daily_queries["value"] > MAX_QUERIES_PER_DAY:
        while my_daily_queries["reset_time"] > datetime.datetime.now():
            time_left = my_daily_queries["reset_time"] - datetime.datetime.now()
            print(f"WARNING : iNaturalist daily queries limit reached, "
                  f"download will resume in {str(time_left).split('.')[0]}", end="\r")
            time.sleep(1)
        print()
        my_daily_queries["value"] = 0
        my_daily_queries["reset_time"] = datetime.datetime.now() + datetime.timedelta(hours=24)


def evaluate_media_rate():
    """wait if the daily query limit has been reached."""
    if my_hourly_media["value"] > MAX_MEDIA_PER_HOUR:
        while my_hourly_media["reset_time"] > datetime.datetime.now():
            time_left = my_hourly_media["reset_time"] - datetime.datetime.now()
            print(f"WARNING : iNaturalist hourly media download limit reached, "
                  f"download will resume in {str(time_left).split('.')[0]}", end="\r")
            time.sleep(1)
        print()
        my_hourly_media["value"] = 0
        my_hourly_media["reset_time"] = datetime.datetime.now() + datetime.timedelta(hours=1)

    if my_daily_media["value"] > MAX_MEDIA_PER_DAY:
        while my_daily_media["reset_time"] > datetime.datetime.now():
            time_left = my_daily_media["reset_time"] - datetime.datetime.now()
            print(f"WARNING : iNaturalist daily media download limit reached, "
                  f"download will resume in {str(time_left).split('.')[0]}", end="\r")
            time.sleep(1)
        print()
        my_daily_media["value"] = 0
        my_daily_media["reset_time"] = datetime.datetime.now() + datetime.timedelta(hours=24)


def download(species_name, observations, image_size, output_dir):
    """
    Download images and metadata from a set of observations. This will return the ID of the last processed observation (used as id_above for the next API page request).
    """
    global current_observations_number
    global current_images_number
    global current_dataset_size

    last_observation_id = None

    for observation in observations:

        # extract obs metadata
        obs_species = observation["taxon"]["name"] if observation.get("taxon") else species_name
        obs_id = observation["id"]
        obs_license = observation.get("license_code") or "none"
        obs_login = observation["user"]["login"]
        obs_quality = observation.get("quality_grade") or "none"
        obs_date = observation.get("observed_on") or "none"

        if observation.get("geojson"):
            obs_longitude = observation["geojson"]["coordinates"][0]
            obs_latitude  = observation["geojson"]["coordinates"][1]
        else:
            obs_latitude  = "none"
            obs_longitude = "none"

        current_observations_number += 1
        print(f"INFO : {species_name} - "
              f"Observation {current_observations_number}/{max_observations_number} "
              f"(ID : {obs_id})")

        # write obs metadata to CSV as one row per photo
        metadata_path = os.path.join(output_dir, f"{species_name.replace(' ', '_')}_metadata.csv")
        with open(metadata_path, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                obs_species,
                obs_id,
                obs_license,
                obs_login,
                obs_quality,
                obs_date,
                obs_latitude,
                obs_longitude,
            ])

        # download obs photo
        images_dir = os.path.join(output_dir, f"{species_name.replace(' ', '_')}_images")
        for photo_idx, photo in enumerate(observation.get("photos", [])):
            image_url = photo["url"].replace("/square", f"/{image_size}")

            file_name = (
                f"{obs_species.replace(' ', '-')}"
                f"_{obs_login}"
                f"_{obs_license}"
                f"_{obs_id}"
                f"_{photo_idx}.jpeg"
            )
            file_path = os.path.join(images_dir, file_name)

            # skip if already downloaded 
            if os.path.exists(file_path):
                print(f"INFO : Skipping already-downloaded image {file_name}")
                continue

            image_response = session.get(image_url)
            if image_response.status_code == 200:
                with open(file_path, "wb") as image_file:
                    image_file.write(image_response.content)

                size_mb = len(image_response.content) / 1_000_000
                current_images_number  += 1
                current_dataset_size   += size_mb
                print(f"INFO : {current_images_number} images downloaded "
                      f"({round(current_dataset_size, 2)} MB)")

                # update media rate-limit counters (stored in GB)
                size_gb = size_mb / 1_000
                my_hourly_media["value"] += size_gb
                my_daily_media["value"]  += size_gb
                evaluate_media_rate()
            else:
                print(f"WARNING : Could not download image at {image_url} "
                      f"(status {image_response.status_code})")

        last_observation_id = obs_id

    return last_observation_id


def main():

    global max_observations_number
    global current_observations_number
    global current_images_number
    global current_dataset_size

    # cmd line args
    parser = argparse.ArgumentParser(
        description="Download images and metadata from iNaturalist for a target species."
    )
    parser.add_argument(
        "-s", "--species",
        required=True,
        help='Species name to search for, e.g. "Rhinecanthus aculeatus"',
    )
    parser.add_argument(
        "-n", "--observations",
        default=200, type=int,
        help="Maximum number of observations to download (default: 200)",
    )
    parser.add_argument(
        "-q", "--quality",
        default="research",
        choices=["research", "needs_id", "casual", "any"],
        help="Observation quality grade (default: research)",
    )
    parser.add_argument(
        "-i", "--image-size",
        default="medium",
        choices=["small", "medium", "large", "original"],
        help="Image size to download (default: medium)",
    )
    parser.add_argument(
        "-l", "--license",
        default="any",
        help=(
            "Photo license filter (default: any). "
            "Options: cc-by, cc-by-nc, cc-by-nc-nd, cc-by-nc-sa, cc-by-nd, cc-by-sa, cc0"
        ),
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="results",
        help="Root directory where images and metadata are saved (default: results/)",
    )
    parser.add_argument(
        "--id-above",
        default=0, type=int,
        help="Start downloading from observations with ID above this value (useful for resuming)",
    )
    args = parser.parse_args()

    species_name = args.species

    print()
    print("-------------------------- SCRIPT STARTED --------------------------")
    print(f"Species: {species_name}")
    print(f"Max obs: {args.observations}")
    print(f"Quality: {args.quality}")
    print(f"Image size: {args.image_size}")
    print(f"License: {args.license}")
    print(f"Output dir: {args.output_dir}")
    print()

    # create output dirs and metadata dirs
    images_dir    = os.path.join(args.output_dir, f"{species_name.replace(' ', '_')}_images")
    metadata_path = os.path.join(args.output_dir, f"{species_name.replace(' ', '_')}_metadata.csv")

    os.makedirs(images_dir, exist_ok=True)

    if not os.path.exists(metadata_path):
        with open(metadata_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                "species_name",
                "observation_id",
                "observation_license",
                "observer_login",
                "observation_quality",
                "observation_date",
                "observation_latitude",
                "observation_longitude",
            ])
    else:
        print(f"WARNING : {metadata_path} already exists — data will be appended.")

    # querying iNaturalist
    quality_param = "" if args.quality == "any" else f"&quality_grade={args.quality}"
    license_param = "" if args.license == "any" else f"&license={args.license}&photo_license={args.license}"

    id_above = args.id_above

    try:
        # 1. find out how many obs are available
        count_url = (
            f"https://api.inaturalist.org/v1/observations?"
            f"taxon_name={species_name}"
            f"{quality_param}"
            f"&has[]=photos"
            f"{license_param}"
            f"&page=1&per_page=1"
            f"&order_by=id&order=asc&id_above={id_above}"
        )
        response = session.get(count_url)
        my_daily_queries["value"] += 1

        total_available = response.json()["total_results"]

        if total_available == 0:
            print(f"WARNING : No observations found for '{species_name}' with the given filters.")
            print()
            print("------------------ SCRIPT TERMINATED SUCCESSFULLY ------------------")
            print()
            return

        if total_available < args.observations:
            print(f"WARNING : Only {total_available} observations available for '{species_name}'.")
            max_observations_number = total_available
        else:
            max_observations_number = args.observations

        print(f"INFO : Downloading {max_observations_number} observations for '{species_name}'")

        # page through observations until we have enough
        while current_observations_number < max_observations_number:
            per_page = min(200, max_observations_number - current_observations_number)

            obs_url = (
                f"https://api.inaturalist.org/v1/observations?"
                f"taxon_name={species_name}"
                f"{quality_param}"
                f"&has[]=photos"
                f"{license_param}"
                f"&page=1&per_page={per_page}"
                f"&order_by=id&order=asc&id_above={id_above}"
            )
            response = session.get(obs_url)
            time.sleep(1.2)  # so that we're not rude to the API lol
            my_daily_queries["value"] += 1
            evaluate_query_rate()

            observations = response.json().get("results", [])
            if not observations:
                print("INFO : No more observations returned by the API.")
                break

            last_id = download(species_name, observations, args.image_size, args.output_dir)
            if last_id is not None:
                id_above = last_id

        print(f"INFO : Download finished — "
              f"{current_observations_number} observations, "
              f"{current_images_number} images, "
              f"{round(current_dataset_size, 2)} MB")

    except requests.exceptions.RequestException as e:
        print(f"ERROR : Connection error — {e}")
        print()
        print("------------------- SCRIPT TERMINATED WITH ERROR -------------------")
        print()
        return
    except FileNotFoundError as e:
        print(f"ERROR : {e.strerror} : {e.filename}")
        print()
        print("------------------- SCRIPT TERMINATED WITH ERROR -------------------")
        print()
        return

    print()
    print("------------------ SCRIPT TERMINATED SUCCESSFULLY ------------------")
    print()


if __name__ == "__main__":
    main()
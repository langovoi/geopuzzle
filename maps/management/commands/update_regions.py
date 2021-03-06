import json
import os
import shutil
from zipfile import ZipFile

import requests
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.core.management import BaseCommand

from django.db import transaction

from maps.models import Region


class Command(BaseCommand):
    def handle(self, *args, **options):
        def import_tree(id):
            def import_region(feature):
                def extract_data(properties):
                    result = {'level': properties['admin_level']}
                    fields = ['boundary', 'ISO3166-1:alpha3', 'timezone']
                    for field in fields:
                        result[field] = properties['tags'].get(field, None)
                    return result

                print(feature['properties']['name'])
                parent = None
                if len(feature['rpath']) > 2:
                    # sometimes they are swapped
                    parent_id = feature['rpath'][1] if int(feature['rpath'][0]) == feature['id'] else \
                    feature['rpath'][0]
                    parent = Region.objects.get(osm_id=parent_id)
                region = Region.objects.create(
                    title=feature['properties']['name'],
                    polygon=GEOSGeometry(json.dumps(feature['geometry'])),
                    parent=parent,
                    wikidata_id=feature['properties']['tags'].get('wikidata'),
                    osm_id=feature['id'],
                    osm_data=extract_data(feature['properties'])
                )
                for lang in ('en', 'ru'):
                    trans = region.load_translation(lang)
                    trans.master = region
                    trans.name = region.title
                    trans.save()

            zip_file = os.path.join(settings.GEOJSON_DIR, '{}.zip'.format(id))
            if not os.path.exists(zip_file):
                url = settings.OSM_URL.format(id=id, key=settings.OSM_KEY)
                print(url)
                response = requests.get(url, stream=True)
                if response.status_code != 200:
                    raise Exception('Bad request')
                with open(zip_file, 'wb') as out_file:
                    response.raw.decode_content = True
                    shutil.copyfileobj(response.raw, out_file)
            zipfile = ZipFile(zip_file)
            zip_names = zipfile.namelist()
            for zip_name in zip_names:
                print(zip_name)
                # if zip_name.endswith('AL2.GeoJson') or zip_name.endswith('AL3.GeoJson') or zip_name.endswith('AL4.GeoJson'):
                # if not zip_name.endswith('AL6.GeoJson'):
                #     continue
                level = json.loads(zipfile.open(zip_name).read().decode())
                not_passed = []
                for feature in level['features']:
                    try:
                        if not Region.objects.filter(osm_id=feature['id']).exists():
                            import_region(feature)
                    except Region.DoesNotExist:
                        not_passed.append(feature)
                        continue
                while len(not_passed) > 0:
                    bad_passed = []
                    for feature in not_passed:
                        try:
                            import_region(feature)
                        except Region.DoesNotExist:
                            bad_passed.append(feature)
                            continue
                    if not_passed == bad_passed:
                        print('Circular references')
                        break
                    not_passed = bad_passed

        with open(os.path.join(settings.GEOJSON_DIR, 'root.json')) as root_file:
            root = json.loads(root_file.read())
        # for country in root:
        #     if country['id'] in ():
        #         continue
        #     print(country['a_attr'])
            # if not Region.objects.filter(osm_id=country['id']).exists():
        with transaction.atomic():
            # import_tree(21335)
            # import_tree(51684)
            # import_tree(2184073)
            # import_tree(295480)
            import_tree(60199)
            # import_tree(1428125)

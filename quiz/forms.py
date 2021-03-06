from typing import List, Dict

from django import forms
from django.db import connection
from django.contrib.gis.geos import Point
from django.utils.translation import get_language

from maps.forms import RegionForm


class PointContainsForm(forms.Form):
    lat = forms.FloatField()
    lng = forms.FloatField()

    CONTAINS_SQL = """SELECT ST_Covers(polygon, p) 
FROM (SELECT polygon from maps_region where id = {id}) As polygon,  
    ST_Point({lon}, {lat}) as p;"""

    def __init__(self, area, *args, **kwargs):
        self.area = area
        super(PointContainsForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(PointContainsForm, self).clean()
        with connection.cursor() as cursor:
            cursor.execute(self.CONTAINS_SQL.format(id=self.area.id, lat=cleaned_data.get('lat'), lon=cleaned_data.get('lng')))
            row = cursor.fetchone()
            result = row[0]
        if not result:
            raise forms.ValidationError('Point not in polygons')


class QuizInfoboxForm(RegionForm):
    params = forms.CharField()

    def clean_params(self) -> List:
        return self.cleaned_data['params'].split(',')

    def json(self) -> Dict:
        def extract_capital(capital) -> str:
            return capital['name'] if isinstance(capital, dict) else capital

        questions = []
        founded = []
        for region in self.regions:
            trans = region.translation
            if trans.infobox is None:
                founded.append(region)
            k = {}
            for param in self.cleaned_data['params']:
                if param == 'capital':
                    capital = trans.infobox.get('capital', None)
                    value = trans.infobox.get('name', None) if capital is None else extract_capital(capital)
                elif param == 'title':
                    value = trans.infobox.get('name', None)
                else:
                    value = trans.infobox.get(param, None)
                if value is not None:
                    k[param] = value

            # if question has not values - set them as founded
            if k != {}:
                k['id'] = region.id
                k['name'] = trans.infobox.get('name', None)
                questions.append(k)
            else:
                founded.append(region.full_info(get_language()))
        return {'questions': questions, 'founded': founded}

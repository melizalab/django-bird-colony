# -*- coding: utf-8 -*-
# -*- mode: python -*-
from django import forms

from django.contrib.auth.models import User
from birds.models import Animal, Event, Status, Location, Color


class BandingForm(forms.Form):
    sire = forms.ModelChoiceField(queryset=Animal.objects.filter(sex__exact='M'))
    dam  = forms.ModelChoiceField(queryset=Animal.objects.filter(sex__exact='F'))
    hatch_date = forms.DateField()
    banding_date = forms.DateField()
    band_color = forms.ModelChoiceField(queryset=Color.objects.all(), required=False)
    band_number = forms.IntegerField(min_value=1)
    location = forms.ModelChoiceField(queryset=Location.objects.all())
    comments = forms.CharField(widget=forms.Textarea, required=False)
    user = forms.ModelChoiceField(queryset=User.objects.all())

    def clean(self):
        super(BandingForm, self).clean()
        try:
            self.cleaned_data['hatch_status'] = Status.objects.get(name__startswith="hatch")
        except:
            raise forms.ValidationError("No 'hatched' status type - add one in admin")
        try:
            self.cleaned_data['band_status'] = Status.objects.get(name__startswith="band")
        except:
            raise forms.ValidationError("No 'banded' status type - add one in admin")
        if ('dam' in self.cleaned_data and 'sire' in self.cleaned_data and
            self.cleaned_data['dam'].species != self.cleaned_data['sire'].species):
            raise forms.ValidationError("Parents must be the same species")
        return self.cleaned_data

    def create_chick(self):
        data = self.cleaned_data
        ret = {'chick': None, 'events': []}
        chick = Animal(species=data['sire'].species, sex='U',
                       band_color=data['band_color'], band_number=data['band_number'])
        chick.save()
        chick.parents.add(data['sire'], data['dam'])
        chick.save()
        evt = Event(animal=chick, date=data['hatch_date'],
                    status=data['hatch_status'],
                    description=data['comments'],
                    location=data['location'],
                    entered_by=data['user'])
        evt.save()
        evt = Event(animal=chick, date=data['banding_date'],
                    status=data['band_status'],
                    location=data['location'],
                    description=chick.band(),
                    entered_by=data['user'])
        evt.save()
        return chick

class ClutchForm(forms.Form):
    sire = forms.ModelChoiceField(queryset=Animal.objects.filter(sex__exact='M'))
    dam  = forms.ModelChoiceField(queryset=Animal.objects.filter(sex__exact='F'))
    chicks = forms.IntegerField(min_value=1)
    hatch_date = forms.DateField()
    location = forms.ModelChoiceField(queryset=Location.objects.all())
    comments = forms.CharField(widget=forms.Textarea, required=False)
    user = forms.ModelChoiceField(queryset=User.objects.all())

    def clean(self):
        super(ClutchForm, self).clean()
        try:
            self.cleaned_data['status'] = Status.objects.get(name__startswith="hatch")
        except:
            raise forms.ValidationError("No 'hatch' status type - add one in admin")
        if ('dam' in self.cleaned_data and 'sire' in self.cleaned_data and
            self.cleaned_data['dam'].species != self.cleaned_data['sire'].species):
            raise forms.ValidationError("Parents must be the same species")
        return self.cleaned_data


    def create_clutch(self):
        ret = {'chicks': [], 'events': []}
        for i in range(self.cleaned_data['chicks']):
            chick = Animal(species=self.cleaned_data['sire'].species, sex='U')
            chick.save()
            chick.parents.add(self.cleaned_data['sire'],
                              self.cleaned_data['dam'])
            chick.save()
            evt = Event(animal=chick, date=self.cleaned_data['hatch_date'],
                        status=self.cleaned_data['status'],
                        description=self.cleaned_data['comments'],
                        location=self.cleaned_data['location'],
                        entered_by=self.cleaned_data['user'])
            evt.save()
            ret['chicks'].append(chick)
            ret['events'].append(evt)
        return ret

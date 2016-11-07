# -*- coding: utf-8 -*-

# Django Clone - https://github.com/mohammadroghani/django-clone
# Copyright © 2016 Mohammad Roghani <mohammadroghani43@gmail.com>
# Copyright © 2016 Amir Keivan Mohtashami <akmohtashami97@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from django.db import models

class Question(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')


class Choice(models.Model):
    question = models.ForeignKey(Question)
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

class Person(models.Model):
    questions = models.ManyToManyField(Question)

class Student(models.Model):
    name = models.CharField(max_length=128)

class Group(models.Model):
    name = models.CharField(max_length=128)
    members = models.ManyToManyField(Student, through='Membership')

class Membership(models.Model):
    student = models.ForeignKey(Student)
    group = models.ForeignKey(Group)

class A(models.Model):
    b = models.ManyToManyField('B')

class B(models.Model):
    c = models.ManyToManyField('C')

class C(models.Model):
    a = models.ManyToManyField('A')

class BigChoice(Choice):
    unique_value = models.CharField(max_length=100, null=True, unique=True)

class BigChoice2(Choice):
    unique_value = models.CharField(max_length=100, null=True, unique=True)
    explicit_rel = models.OneToOneField(Choice, parent_link=True)


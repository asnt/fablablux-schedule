# FabLab Luxembourg Schedule Scanner

Scan the wall schedule in FabLab Luxembourg and publish it online during open
access hours.

## Overview

For fair usage time of the machines during open access hours, the users of
FabLab Luxembourg have to book their time slots on site.
To do this, they grab a card from the painted wall schedule.

![FabLab Luxembourg wall schedule](data/wall_small.jpg)

This software aims at automatically publishing the on-site schedule on FabLab
Luxembourg's website at regular intervals.
The online schedule is accessible at http://fablablux.org/oa-schedule/ during
open access hours.

## Architecture

On a Raspberry Pi equipped with a camera, a service:
 * scans the wall schedule periodically;
 * analyses the image for booked time slots (i.e., grabbed cards);
 * pushes the results through a REST API to the target website.

On the website, a WordPress plugin:
 * provides a REST API to receive the schedule updates;
 * displays the schedule;
 * provides a configuration interface.

## Features

The software is robust against perspective deformation in the image due to a
camera looking at the schedule from the side.
In fact, the software first aligns the observed image with a reference one
before analysis.

The WordPress plugin displays the schedule on the website through a short tag
for easy integration.

We can configure when to display the schedule on the website, e.g. for matching
open access hours.

## Installation

## Configuration

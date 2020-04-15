#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
import sys

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

# TODO: connect to a local postgresql database
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#


class Genre(db.Model):
    __tablename__ = "genres"

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String(), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'))
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'))

    def __repr__(self):
        return f'<Genre id: {self.id}, name: {self.name}>'


class Show(db.Model):
    __tablename__ = 'shows'
    id = db.Column(db.Integer, primary_key=True)
    past_show = db.Column(db.Boolean, nullable=False, default=True)
    start_time = db.Column(db.String(), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'))
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'))

    def __repr__(self):
        return f'<Show id: {self.id}, name: {self.start_time}>'


class Venue(db.Model):
    __tablename__ = 'venues'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String())
    seeking_talent = db.Column(db.Boolean)
    seeking_description = db.Column(db.String())
    genres = db.relationship('Genre', backref="venue",
                             lazy=True, collection_class=list, cascade="all,delete")
    shows = db.relationship('Show', backref="venue_shows",
                            lazy=True, collection_class=list, cascade="all,delete")

    def __repr__(self):
        return f'<Venue id:{self.id}, name: {self.name} >'


class Artist(db.Model):
    __tablename__ = 'artists'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.relationship('Genre', backref="artist",
                             lazy=True, collection_class=list)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String())
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String())
    shows = db.relationship('Show', backref="artist_shows",
                            lazy=True, collection_class=list, cascade="all,delete")

    def __repr__(self):
        return f'<Artist id:{self.id}, name: {self.name} >'

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    unique_cities = [(venue.city, venue.state)
                     for venue in Venue.query.distinct(Venue.city).all()]
    data = []

    for city, state in unique_cities:
        city_venues = {}
        city_venues['city'] = city
        city_venues['state'] = state
        city_venues['venues'] = []
        for venue in Venue.query.filter_by(city=city).all():
            venue_data = {}
            venue_data['id'] = venue.id
            venue_data['name'] = venue.name
            venue_data['num_upcoming_shows'] = len(
                list(filter(lambda x: not x.past_show, venue.shows)))
            city_venues['venues'].append(venue_data)
        data.append(city_venues)

    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_term = request.form.get('search_term', '')
    venues_name = [venue.name for venue in Venue.query.all()]
    filter_names = list(
        filter(lambda x: search_term.lower() in x.lower(), venues_name))
    response = {}
    response["count"] = len(filter_names)
    response["data"] = []

    for name in filter_names:
        filtered_venue = Venue.query.filter_by(name=name).first()
        venue_data = {}
        venue_data["name"] = name
        venue_data["id"] = filtered_venue.id
        venue_data["num_upcoming_shows"] = len(
            list(filter(lambda x: not x.past_show, filtered_venue.shows)))
        response["data"].append(venue_data)

    return render_template('pages/search_venues.html', results=response, search_term=search_term)


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    data = Venue.query.get(venue_id)
    past_shows = list(filter(lambda x: x.past_show, data.shows))
    upcoming_shows = list(filter(lambda x: not x.past_show, data.shows))
    past_shows_count = len(past_shows)
    upcoming_shows_count = len(upcoming_shows)
    return render_template('pages/show_venue.html', venue=data,
                           past_shows=past_shows, upcoming_shows=upcoming_shows,
                           past_shows_count=past_shows_count,
                           upcoming_shows_count=upcoming_shows_count)

#  Create Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    form = VenueForm(request.form)
    try:
        venue = Venue(
            name=form.name.data.capitalize(),
            city=form.city.data.capitalize(),
            state=form.state.data,
            address=form.address.data,
            image_link=form.image_link.data,
            facebook_link=form.facebook_link.data,
            genres=[Genre(name=val) for val in form.genres.data]
        )
        db.session.add(venue)
        db.session.commit()
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
    except:
        db.session.rollback()
        print(sys.exc_info())
        flash('An error occurred. Venue ' +
              form.name.data + ' could not be listed.')
    finally:
        db.session.close()

    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    success = True
    try:
        Venue.query.filter_by(id=venue_id).delete()
        db.session.commit()
        flash('The venue was successfully deleted')
    except:
        success = False
        db.session.rollback()
        flash('An error occurred.')
    finally:
        db.session.close()
    if success:
        render_template('pages/home.html')

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    return render_template('pages/artists.html', artists=Artist.query.all())


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form.get('search_term', '')
    artist_name = [artist.name for artist in Artist.query.all()]
    filter_names = list(
        filter(lambda x: search_term.lower() in x.lower(), artist_name))
    response = {}
    response["count"] = len(filter_names)
    response["data"] = []

    for name in filter_names:
        filtered_artist = Artist.query.filter_by(name=name).first()
        artist_data = {}
        artist_data["name"] = name
        artist_data["id"] = filtered_artist.id
        artist_data["num_upcoming_shows"] = len(
            list(filter(lambda x: not x.past_show, filtered_artist.shows)))
        response["data"].append(artist_data)
    return render_template('pages/search_artists.html', results=response, search_term=search_term)


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    data = Artist.query.get(artist_id)
    past_shows = list(filter(lambda x: x.past_show, data.shows))
    upcoming_shows = list(filter(lambda x: not x.past_show, data.shows))
    past_shows_count = len(past_shows)
    upcoming_shows_count = len(upcoming_shows)
    return render_template('pages/show_artist.html', artist=data,
                           past_shows=past_shows, upcoming_shows=upcoming_shows,
                           past_shows_count=past_shows_count,
                           upcoming_shows_count=upcoming_shows_count)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    artist = Artist.query.get(artist_id)
    form = ArtistForm(obj=artist)
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    form = ArtistForm(request.form)
    try:
        artist = Artist.query.get(artist_id)
        artist.name = form.name.data.capitalize(),
        artist.city = form.city.data.capitalize(),
        artist.state = form.state.data,
        artist.phone = form.phone.data,
        artist.facebook_link = form.facebook_link.data,
        artist.genres = [Genre(name=val) for val in form.genres.data]
        db.session.commit()
    except:
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    venue = Venue.query.get(venue_id)
    form = VenueForm(obj=venue)

    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    form = VenueForm(request.form)
    try:
        venue = Venue.query.get(artist_id)
        venue.name = form.name.data.capitalize(),
        venue.city = form.city.data.capitalize(),
        venue.state = form.state.data,
        venue.address = form.address.data,
        venue.phone = form.phone.data,
        venue.facebook_link = form.facebook_link.data,
        venue.genres = [Genre(name=val) for val in form.genres.data]
        db.session.commit()
    except:
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    form = ArtistForm(request.form)
    try:
        artist = Artist(
            name=form.name.data.capitalize(),
            city=form.city.data.capitalize(),
            state=form.state.data,
            phone=form.phone.data,
            facebook_link=form.facebook_link.data,
            genres=[Genre(name=val) for val in form.genres.data]
        )
        db.session.add(artist)
        db.session.commit()
        flash('Artist ' + request.form['name'] + ' was successfully listed!')
    except:
        db.session.rollback()
        print(sys.exc_info())
        flash('An error occurred. Artist ' +
              form.name.data + ' could not be listed.')
    finally:
        db.session.close()
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    data = Show.query.all()
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    form = ShowForm(request.form)
    try:
        show = Show(
            artist_id=form.artist_id.data,
            venue_id=form.venue_id.data,
            start_time=form.start_time.data
        )
        db.session.add(show)
        db.session.commit()
        flash('how was successfully listed!')
    except:
        db.session.rollback()
        print(sys.exc_info())
        flash('An error occurred. Show could not be listed.')
    finally:
        db.session.close()
    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run(debug=True)

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''

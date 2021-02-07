# Silenda
A Django project to host puzzlehunts.

**Organization note**: All code in this repo should be hunt-agnostic. All 2021 MH specific code is in the 2021-hunt repo and is designed as a separate Django module to be symlinked into this repo.

## Quickstart

1. Install python3 and pip3 and `libmysqlclient-dev`.
2. `pip3 install -r requirements.txt`: Install python requirements. May want to consider doing this in a [python virtual environment](https://docs.python.org/3/library/venv.html).
3. Clone the `2021-hunt` repo and symlink its folder to the root of this repo.
    - Example: `ln -s ../2021-hunt .`
4. At this point you can either A. run with a MySQL database locally or B. proxy to our google cloud MySQL database.
    1. For option A:
        1. Install `mysql-server`
        2. Create a MySQL hunt database. Default dev settings in `silenda/settings/dev.py` are:
            - db name: `hunt2021`
            - user: `hunt`
            - password: `hunt`
            - User should have all privileges on the db.
            - Use utf8mb4 encodings
        3. Perform an initial database migration: `DJANGO_ENV=dev python3 manage.py migrate`
        4. Create a django superuser for use with the admin dashboard: `DJANGO_ENV=dev python3 manage.py createsuperuser`
            - Doesn't really matter what you use for username and password.
    2. For option B:
        1.  Use CloudSQL proxy to port 4206 (cloud_sql_proxy -instances="<CLOUD_SQL_INSTANCE>"=tcp:4206)
        2. **IMPORTANT**: For the future steps, replace `DJANGO_ENV=dev` with `DJANGO_ENV=prod`
5. Run a redis server at port 6379.
9. Collect static files: `DJANGO_ENV=dev python3 manage.py collectstatic`
10. Run the Django dev server: `DJANGO_ENV=dev python3 manage.py runserver`
11. Visit `http://localhost:8000` to access the site
  - Go to `/admin` to login to the admin panel with the superuser you created earlier
  - Login at `/login` as one of the teams (defined in `2021-hunt/data/teams.tsv`) to pretend to hunt (Must import teams, puzzles, and launch the hunt to do this, see "Administering the hunt" below)

## Updating

If you run into uniqueness constraint issues when migrating, you may need to flush the whole DB and then migrate:

DJANGO_ENV=dev python3 manage.py flush
DJANGO_ENV=dev python3 manage.py migrate

You'll need to recreate a super user and reimport all the data.

## Administering the hunt

Currently the hunt is administered as follows:

1. `DJANGO_ENV=dev python3 manage.py import_teams`: Import teams from `2021-hunt/data/teams.tsv`
2. `DJANGO_ENV=dev python3 manage.py import_puzzles`: Import teams from `2021-hunt/data/puzzles.tsv`
3. `DJANGO_ENV=dev python3 manage.py launch`: Start the hunt for all teams


## Setting up MySQL

A couple of brief steps for setting up MySQL if you are on Linux:
```
sudo apt-get install mysql-server mysql-client
sudo service mysql start
sudo mysql -u root

CREATE USER 'hunt'@'localhost' IDENTIFIED BY 'hunt';
CREATE DATABASE hunt2021 CHARACTER SET utf8mb4;
GRANT ALL PRIVILEGES ON hunt2021.* TO 'hunt'@'localhost';
exit;
```

## Acknowledgements
Based on spoilr (https://github.com/mysteryhunt/spoilr)

Originally created for 2014 Mystery Hunt
By Jamie Clark (sbj@dimins.org) with some help from Ben O'Connor (benoc@alum.mit.edu)

Updated for the 2015 Mystery Hunt
By Random Hall Mystery Hunt Writing Team (https://github.com/random-hunt/)

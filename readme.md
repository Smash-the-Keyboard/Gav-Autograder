# Gav Autograder

This is a Django-based website for automatically grading simple C++ programs in an educational setting, akin to [Kattis](https://www.kattis.com) or [Autograder.io](https://autograder.io). I started it as part of my Summer 2019 internship at Gavilan College (hence the name), as a continuation of [a previous project by Jeron Wong](https://github.com/ThisIsJeron/Autograder) and continued to work on it occasionally over the next 3 years. It was completed satisfying all of the design requirements, but unfortunately due to external factors it ended up not being used.

The purpose of this git repository is to serve as an archive of the project for anyone interested and as a demonstration of my programming ability.

## Setup

The website is intended to be hosted on an Apache web server using WSGI middleware, and was configured and designed with a MariaDB database in mind. I tested it on Ubuntu 18.04.6 Bionic, but other versions will probably work just as well.

Follow the [official guide](https://docs.djangoproject.com/en/4.1/howto/deployment/wsgi/modwsgi/) to using Django with Apache and `mod_wsgi`, and make sure to read the sections on [Using `mod_wsgi` daemon mode](https://docs.djangoproject.com/en/4.1/howto/deployment/wsgi/modwsgi/#using-mod-wsgi-daemon-mode) and [Serving files](https://docs.djangoproject.com/en/4.1/howto/deployment/wsgi/modwsgi/#serving-files).

I also recommend setting file permissions appropriately to prevent any problems with the server not having access to its own files.

After configuring Apache, the Django site itself also needs to be configured.

All of the python packages that this site requires are listed in the `requirements.txt` file, so they can be installed easily with pip.

A file named `.env` must exist in the base directory, specifying the path to a JSON config file for the site, like so:
```
AUTOGRADER_CONFIG='/path/to/config-file.json'
```

The config file should be of the following format.

```
{
    "SECRET_KEY": "",
    "SITE_HOST": "",
    "DB_NAME": "",
    "DB_USER": "",
    "DB_PASS": "",
    "DB_PORT": "",
    "DB_OPTIONS": {},
    "EMAIL_USER": "",
    "EMAIL_PASS": ""
}
```

`EMAIL_USER` and `EMAIL_PASS` may be left blank, I never confirmed whether that was working. The other settings are up to you, and correspond to their respective entries in `settings.py`.

Lastly, this site requires that Docker be installed. Make sure to build an image from the file `Base.Dockerfile` so the user-uploaded programs can be tested.

## Final Notes

If anyone has any questions about this project or would like to contribute to it, feel free to contact me, and I'll get back to you when I can.
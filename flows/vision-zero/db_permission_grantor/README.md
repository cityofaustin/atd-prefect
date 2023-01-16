# Database Permission Maintenance Script / ETL

## Purpose
From time to time, in the development process, tables are added to the Vision Zero database. These tables are created without the needed permissions for access by the staff accounts, which are used via the read-replica to access the database and to download its contents via pg_dump. 

Additionally, when the CRIS import script runs, it drops and recreates the `import` schema which removes any permissions that may have been had by staff users used to access it.

This script re-grants access to the staff role, which in turns grants it to the members of that role, meaning the staff themselves.

## Setup

The roles are configured at the database level. Create a staff role:

```
CREATE ROLE staff NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOLOGIN NOREPLICATION NOBYPASSRLS;
```

Roles for each staff member are also created at the database level. Create staff roles, if required, and add them to the staff role.

```
grant staff to user01;
grant staff to user02;
```
# Router

## Routes - sync github
- [ ] crear ruta POST `/github/sync/`
  - [ ] Extraer repositorios de github
  - [ ] Almacena la informacion en mondodb
  - [ ] returnar {"status": "success"}
- [ ] crear ruta GET `/github/`
  - [ ] Returna la lista en mondodb
- [ ] crear ruta GET `/github/{repositorio}`
  - [ ] Identifica si el repositorio existe en la base de datos mongodb
  - [ ] extraer la siguiente informacion
    - [ ] Nombre del repositorio
    - [ ] Usuarios que han contribuido
    - [ ] Existe en codepipeline de AWS
    - [ ] Tiene github actions
    - [ ] Tiene el modelo de github flow
    - [ ] Tiene archivo de configuracion backsatge

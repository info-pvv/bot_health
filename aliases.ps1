# aliases.ps1 - Псевдонимы для удобства
function docker-compose {
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        docker-compose @args
    } else {
        docker compose @args
    }
}

# Экспорт функции
Export-ModuleMember -Function docker-compose.\
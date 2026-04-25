output "api_url" {
  value       = "https://${azurerm_linux_web_app.api.default_hostname}"
  description = "Backend API URL"
}

output "frontend_url" {
  value       = "https://${azurerm_linux_web_app.frontend.default_hostname}"
  description = "Frontend URL"
}

output "cdn_endpoint" {
  value       = "https://${azurerm_cdn_endpoint.frontend.host_name}"
  description = "CDN endpoint URL"
}

output "acr_login_server" {
  value       = azurerm_container_registry.main.login_server
  description = "Container registry login server"
}

output "postgres_fqdn" {
  value       = azurerm_postgresql_flexible_server.main.fqdn
  description = "PostgreSQL FQDN"
}

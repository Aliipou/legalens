variable "prefix" {
  description = "Prefix for all resource names"
  type        = string
  default     = "legalens"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "northeurope"
}

variable "resource_group" {
  description = "Azure resource group name"
  type        = string
  default     = "legalens-prod"
}

variable "db_admin_user" {
  description = "PostgreSQL admin username"
  type        = string
  default     = "legalens_admin"
  sensitive   = true
}

variable "db_admin_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

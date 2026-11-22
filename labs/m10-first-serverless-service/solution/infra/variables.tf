variable "region" {
  description = "AWS Region of the lab."
  type        = string
  default     = "eu-west-3"
}

variable "project_name" {
  description = "Prefix of every resource name."
  type        = string
  default     = "registre-prompts"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,40}$", var.project_name))
    error_message = "project_name must be kebab-case, 3 to 41 characters."
  }
}

variable "tags" {
  description = "Tags applied to every resource through the provider default_tags."
  type        = map(string)
  default = {
    Projet        = "formation-m10"
    Environnement = "lab"
  }
}

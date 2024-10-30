output "policy_dashboard_user_pool" {
  value = module.cognito.user_pool
}

output "policy_dashboard_user_pool_id" {
  value = module.cognito.user_pool_id
}

output "policy_dashboard_user_pool_arn" {

  value = module.cognito.user_pool_arn

}

output "policy_dashboard_user_pool_domain" {
  value = module.cognito.user_pool_domain
}

output "policy_dashboard_user_pool_client" {
  value = module.cognito.user_pool_client
}

output "policy_dashboard_user_pool_client_id" {
  value = module.cognito.user_pool_client_id
}

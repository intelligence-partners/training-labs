# Step 9: the SNS topic and three alarms.

resource "aws_sns_topic" "alertes" {
  name = "m14-alertes"
}

# Confirm the subscription from the email you receive. An unconfirmed subscription cannot be
# deleted by Terraform; deleting the topic deletes it.
resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alertes.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Average cost per task.
resource "aws_cloudwatch_metric_alarm" "cout_moyen_tache" {
  alarm_name          = "m14-cout-moyen-tache"
  alarm_description   = "Coût moyen par tâche au-dessus du double de la référence v1"
  namespace           = local.namespace
  metric_name         = "CoutTacheUSD"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 1
  threshold           = var.cost_alarm_threshold
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alertes.arn]
  ok_actions          = [aws_sns_topic.alertes.arn]
}

# Success rate, computed from two metrics.
resource "aws_cloudwatch_metric_alarm" "taux_reussite" {
  alarm_name          = "m14-taux-reussite"
  alarm_description   = "Taux de tâches réussies sous 75 %"
  comparison_operator = "LessThanThreshold"
  threshold           = 75
  evaluation_periods  = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alertes.arn]

  metric_query {
    id          = "ok"
    return_data = false
    metric {
      namespace   = local.namespace
      metric_name = "TacheReussie"
      period      = 300
      stat        = "Sum"
    }
  }

  metric_query {
    id          = "tot"
    return_data = false
    metric {
      namespace   = local.namespace
      metric_name = "TacheTerminee"
      period      = 300
      stat        = "Sum"
    }
  }

  metric_query {
    id          = "taux"
    expression  = "100 * ok / tot"
    label       = "Réussite (%)"
    return_data = true
  }
}

# Cache read rate: the solution of the step 9 exercise.
resource "aws_cloudwatch_metric_alarm" "taux_cache" {
  alarm_name          = "m14-taux-cache"
  alarm_description   = "Moins de 50 % de l'entrée lue depuis le cache"
  comparison_operator = "LessThanThreshold"
  threshold           = 50
  evaluation_periods  = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alertes.arn]

  metric_query {
    id          = "lus"
    return_data = false
    metric {
      namespace   = local.namespace
      metric_name = "TokensLusEnCache"
      period      = 300
      stat        = "Sum"
    }
  }

  metric_query {
    id          = "tot"
    return_data = false
    metric {
      namespace   = local.namespace
      metric_name = "TokensEntreeTotal"
      period      = 300
      stat        = "Sum"
    }
  }

  metric_query {
    id          = "taux"
    expression  = "100 * lus / tot"
    label       = "Lecture du cache (%)"
    return_data = true
  }
}

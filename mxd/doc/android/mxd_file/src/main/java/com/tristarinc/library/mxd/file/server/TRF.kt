package com.tristarinc.library.mxd.file.server

import com.tristarinc.library.mxd.MXDError
import com.tristarinc.library.mxd.file.MXD
import com.tristarinc.library.mxd.file.bean.*

class TRF : MXD() {

    val Holidays = Holidays()
    val SpecialDays = SpecialDays()
    val TariffSet = TariffSet()

    override fun parse(listener: Listener?, data: ByteArray, checkCRC: Boolean, saveData: Boolean, readSchemaAndData: Boolean): MXDError {

        val superResult = super.parse(listener, data, checkCRC, saveData, readSchemaAndData)
        if (superResult != MXDError.Success) {
            return superResult
        }

        for (sc in schema) {
            when (sc.fieldName) {
                Holidays::class.simpleName -> {
                    for (element in sc.elements) {
                        if (element.fieldName == Date::class.simpleName) {
                            for (sElement in element.elements) {
                                val date = Date()
                                for (ssElement in sElement.elements) {
                                    when (ssElement.fieldName) {
                                        "Day" -> {
                                            date.Day = ssElement.getDataInt(0)
                                        }
                                        "Month" -> {
                                            date.Month = ssElement.getDataInt(0)
                                        }
                                        "Year" -> {
                                            date.Year = ssElement.getDataInt(0)
                                        }
                                    }
                                }
                                Holidays.Date.add(date)
                            }
                        }
                    }
                }
                SpecialDays::class.simpleName -> {
                    for (element in sc.elements) {
                        if (element.fieldName == Date::class.simpleName) {
                            for (sElement in element.elements) {
                                val date = Date()
                                for (ssElement in sElement.elements) {
                                    when (ssElement.fieldName) {
                                        "Day" -> {
                                            date.Day = ssElement.getDataInt(0)
                                        }
                                        "Month" -> {
                                            date.Month = ssElement.getDataInt(0)
                                        }
                                        "Year" -> {
                                            date.Year = ssElement.getDataInt(0)
                                        }
                                    }
                                }
                                SpecialDays.Date.add(date)
                            }
                        }
                    }
                }
                TariffSet::class.simpleName -> {
                    for (element in sc.elements) {
                        when (element.fieldName) {
                            "Description" -> {
                                TariffSet.Description = element.data.utf8 ?: ""
                            }
                            CategoryMap::class.simpleName -> {
                                for (sElement in element.elements) {
                                    val categoryMap = CategoryMap()
                                    for (ssElement in sElement.elements) {
                                        when (ssElement.fieldName) {
                                            "Category" -> {
                                                categoryMap.Category = ssElement.getDataInt(0)
                                            }
                                            "RuleSet" -> {
                                                categoryMap.RuleSet = ssElement.getDataInt(0)
                                            }
                                        }
                                    }
                                    TariffSet.CategoryMap.add(categoryMap)
                                }
                            }
                            Tariff::class.simpleName -> {
                                for (sElement in element.elements) {
                                    val tariff = Tariff()
                                    for (ssElement in sElement.elements) {
                                        when (ssElement.fieldName) {
                                            "Description" -> {
                                                tariff.Description = ssElement.data.utf8 ?: ""
                                            }
                                            "StartDay" -> {
                                                tariff.StartDay = ssElement.getDataInt(0)
                                            }
                                            "StartMonth" -> {
                                                tariff.StartMonth = ssElement.getDataInt(0)
                                            }
                                            "StartYear" -> {
                                                tariff.StartYear = ssElement.getDataInt(0)
                                            }
                                            "EndDay" -> {
                                                tariff.EndDay = ssElement.getDataInt(0)
                                            }
                                            "EndMonth" -> {
                                                tariff.EndMonth = ssElement.getDataInt(0)
                                            }
                                            "EndYear" -> {
                                                tariff.EndYear = ssElement.getDataInt(0)
                                            }
                                            "RuleSet" -> {
                                                for (sssElement in ssElement.elements) {
                                                    val rulSet = RuleSet()
                                                    for (ssssElement in sssElement.elements) {
                                                        when (ssssElement.fieldName) {
                                                            "CalculationType" -> {
                                                                rulSet.CalculationType = ssssElement.data.utf8 ?: ""
                                                            }
                                                            "FreeTimeOption" -> {
                                                                rulSet.FreeTimeOption = ssssElement.data.utf8 ?: ""
                                                            }
                                                            "ClosedTimeOption" -> {
                                                                rulSet.ClosedTimeOption = ssssElement.data.utf8 ?: ""
                                                            }
                                                            "AllowOverpayment" -> {
                                                                rulSet.AllowOverpayment = ssssElement.data.bool ?: false
                                                            }
                                                            "StealRemainder" -> {
                                                                rulSet.StealRemainder = ssssElement.data.bool ?: false
                                                            }
                                                            "AllowFreeIssue" -> {
                                                                rulSet.AllowFreeIssue = ssssElement.data.bool ?: false
                                                            }
                                                            "WalkTime" -> {
                                                                rulSet.WalkTime = ssssElement.getDataInt(0)
                                                            }
                                                            "StepFollowsTariff" -> {
                                                                rulSet.StepFollowsTariff = ssssElement.data.bool ?: false
                                                            }
                                                            "DefaultStepValue" -> {
                                                                rulSet.DefaultStepValue = ssssElement.getDataInt(0)
                                                            }
                                                            "LimitValueType" -> {
                                                                rulSet.LimitValueType = ssssElement.data.utf8 ?: ""
                                                            }
                                                            "TariffCodeType" -> {
                                                                rulSet.TariffCodeType = ssssElement.data.utf8 ?: ""
                                                            }
                                                            "VATRate" -> {
                                                                rulSet.VATRate = ssssElement.getDataInt(0)
                                                            }
                                                            "Description" -> {
                                                                rulSet.Description = ssssElement.data.utf8 ?: ""
                                                            }
                                                            "RuleProperties" -> {
                                                                for (sssssElement in ssssElement.elements) {
                                                                    val ruleProperty = RuleProperties()
                                                                    for (ssssssElement in sssssElement.elements) {
                                                                        when (ssssssElement.fieldName) {
                                                                            "MinValue" -> {
                                                                                ruleProperty.MinValue = ssssssElement.getDataInt(0)
                                                                            }
                                                                            "MaxValue" -> {
                                                                                ruleProperty.MaxValue = ssssssElement.getDataInt(0)
                                                                            }
                                                                            "MaxExpiryTime" -> {
                                                                                ruleProperty.MaxExpiryTime = ssssssElement.getDataInt(0)
                                                                            }
                                                                            "MaxValueAction" -> {
                                                                                ruleProperty.MaxValueAction = ssssssElement.data.utf8 ?: ""
                                                                            }
                                                                            "MaxOverpayment" -> {
                                                                                ruleProperty.MaxOverpayment = ssssssElement.getDataInt(0)
                                                                            }
                                                                            "MessageNumber" -> {
                                                                                ruleProperty.MessageNumber = ssssssElement.getDataInt(0)
                                                                            }
                                                                            "TicketLayout" -> {
                                                                                ruleProperty.TicketLayout = ssssssElement.getDataInt(0)
                                                                            }
                                                                            "AuditCode" -> {
                                                                                ruleProperty.AuditCode = ssssssElement.data.utf8 ?: ""
                                                                            }
                                                                            "FormNumber" -> {
                                                                                ruleProperty.FormNumber = ssssssElement.getDataInt(0)
                                                                            }
                                                                        }
                                                                    }
                                                                    rulSet.RuleProperties.add(ruleProperty)
                                                                }
                                                            }
                                                            "TariffCode" -> {
                                                                for (sssssElement in ssssElement.elements) {
                                                                    val tariffCode = TariffCode()
                                                                    for (ssssssElement in sssssElement.elements) {
                                                                        when (ssssssElement.fieldName) {
                                                                            "Value" -> {
                                                                                tariffCode.Value = ssssssElement.getDataInt(0)
                                                                            }
                                                                            "AuditCode" -> {
                                                                                tariffCode.AuditCode = ssssssElement.data.utf8 ?: ""
                                                                            }
                                                                        }
                                                                    }
                                                                    rulSet.TariffCode.add(tariffCode)
                                                                }
                                                            }
                                                            "TariffRule" -> {
                                                                for (sssssElement in ssssElement.elements) {
                                                                    val tariffRule = TariffRule()
                                                                    for (ssssssElement in sssssElement.elements) {
                                                                        when (ssssssElement.fieldName) {
                                                                            "RuleType" -> {
                                                                                tariffRule.RuleType = ssssssElement.data.utf8 ?: ""
                                                                            }
                                                                            "Priority" -> {
                                                                                tariffRule.Priority = ssssssElement.getDataInt(0)
                                                                            }
                                                                            "StartHour" -> {
                                                                                tariffRule.StartHour = ssssssElement.getDataInt(0)
                                                                            }
                                                                            "StartMinute" -> {
                                                                                tariffRule.StartMinute = ssssssElement.getDataInt(0)
                                                                            }
                                                                            "EndHour" -> {
                                                                                tariffRule.EndHour = ssssssElement.getDataInt(0)
                                                                            }
                                                                            "EndMinute" -> {
                                                                                tariffRule.EndMinute = ssssssElement.getDataInt(0)
                                                                            }
                                                                            "DaysAvailable" -> {
                                                                                tariffRule.DaysAvailable = ssssssElement.getDataInt(0)
                                                                            }
                                                                            "LimitType" -> {
                                                                                tariffRule.LimitType = ssssssElement.data.utf8 ?: ""
                                                                            }
                                                                            "ValidAfter" -> {
                                                                                tariffRule.ValidAfter = ssssssElement.getDataInt(0)
                                                                            }
                                                                            "ValidUntil" -> {
                                                                                tariffRule.ValidUntil = ssssssElement.getDataInt(0)
                                                                            }
                                                                            "StopOnLimit" -> {
                                                                                tariffRule.StopOnLimit = ssssssElement.data.bool ?: false
                                                                            }
                                                                            "PropertiesIndex" -> {
                                                                                tariffRule.PropertiesIndex = ssssssElement.getDataInt(0)
                                                                            }
                                                                            "Cost" -> {
                                                                                tariffRule.Cost = ssssssElement.getDataInt(0)
                                                                            }
                                                                            "TimeBought" -> {
                                                                                tariffRule.TimeBought = ssssssElement.getDataInt(0)
                                                                            }
                                                                            "TimeBoughtType" -> {
                                                                                tariffRule.TimeBoughtType = ssssssElement.data.utf8 ?: ""
                                                                            }
                                                                            "AddPeriod" -> {
                                                                                tariffRule.AddPeriod = ssssssElement.getDataInt(0)
                                                                            }
                                                                            "AddPeriodType" -> {
                                                                                tariffRule.AddPeriodType = ssssssElement.data.utf8 ?: ""
                                                                            }
                                                                            "AuditCode" -> {
                                                                                tariffRule.AuditCode = ssssssElement.data.utf8 ?: ""
                                                                            }
                                                                        }
                                                                    }
                                                                    rulSet.TariffRule.add(tariffRule)
                                                                }
                                                            }
                                                        }
                                                    }
                                                    tariff.RuleSet.add(rulSet)
                                                }
                                            }
                                        }
                                    }
                                    TariffSet.Tariff.add(tariff)
                                }
                            }
                        }
                    }
                }
            }
        }

        return MXDError.Success
    }
}
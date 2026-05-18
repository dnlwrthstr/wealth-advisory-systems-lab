from __future__ import annotations
from typing import List, Optional, Any, Union, Dict
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, RootModel
from enum import Enum

class FinancialInstrument(BaseModel):
    """
    Financial instrument entity (root of the hierarchy).
    """
    longName: Optional[LongText] = Field(None, description="Name of the financial instrument in free text.")
    shortName: Optional[ShortText] = Field(None, description="Short name of the financial instrument.")
    identificationList: Optional[List[FinancialInstrumentIdentification]] = Field(None, description="List of instrument identifications.")
    cfiCode: Optional[CfiCode] = Field(None, description="CFI classification code of the instrument.")

class Currency(RootModel):
    """
    ISO 4217 alphabetic currency code.
    """
    root: str

class LegalEntityIdentifier(RootModel):
    """
    Legal Entity Identifier (LEI) according to ISO 17442.
    """
    root: str

class CurrencyPair(RootModel):
    """
    Currency pair expressed as BASE/QUOTE (e.g., EUR/USD).
    """
    root: str

class ForwardRate(RootModel):
    """
    Agreed FX forward rate for the settlement date.
    """
    root: Decimal

class CreditSupport(str, Enum):
    """
    Credit support or collateral agreement governing the FX forward.
    """
    csa_agreement = "csa_agreement"
    margin_agreement = "margin_agreement"
    other = "other"

class ContractSize(RootModel):
    """
    Contract size of an instrument.
    """
    root: float

class TickSize(RootModel):
    """
    Minimum price fluctuation (tick size) for a traded contract.
    """
    root: float

class ExpiryCode(RootModel):
    """
    Contract expiry code representing month and year (e.g., H6).
    """
    root: str

class OptionType(str, Enum):
    """
    Specifies whether it is a Call option (right to purchase a specific underlying asset) or a Put option (right to sell a specific underlying asset).

    """
    call = "call"
    put = "put"

class OptionStyle(str, Enum):
    """
    Specifies how an option can be exercised.
    """
    american = "american"
    european = "european"
    bermudan = "bermudan"
    asian = "asian"

class Price(BaseModel):
    """
    Price entity with type, numeric value, and optional currency.
    """
    type: str = Field(..., description="Indicates whether the price is an actual currency amount per unit or a percentage. ")
    value: Decimal = Field(..., description="Signed decimal price value.")
    currency: Optional[Currency] = Field(None, description="Currency of the price, if applicable.")

class CurrencyAmount(BaseModel):
    """
    Amount denoted in a given currency.
    """
    amount: Decimal = Field(..., description="Signed amount.")
    currency: Currency = Field(..., description="Currency of the amount.")

class DayCountBasis(str, Enum):
    """
    Day count convention used for interest calculation.
    """
    act_360 = "act_360"
    act_365 = "act_365"
    act_act_icma = "act_act_icma"
    act_act_isda = "act_act_isda"
    act_act_afb = "act_act_afb"
    act_365l = "act_365l"
    bus_252 = "bus_252"
    u30_360 = "u30_360"
    u30e_360_icma = "u30e_360_icma"
    u30e_360_isda = "u30e_360_isda"
    u30e_360 = "u30e_360"
    u30u_360 = "u30u_360"

class InterestRate(BaseModel):
    """
    Per annum interest rate definition, including type (fixed/variable/ staggered), optional value, basis, and payment characteristics.

    """
    type: str = Field(..., description="Type of interest: - fixed: fixed interest rate - variable: floating rate based on a benchmark - staggered: rate set at different levels for different periods ")
    value: Optional[float] = Field(None, description="Current rate as decimal (e.g. 0.00125).")
    dayCountBasis: Optional[DayCountBasis] = Field(None, description="Day count basis for interest calculation.")
    paymentDate: Optional[date] = Field(None, description="Date of the next interest payment.")
    paymentFrequency: Optional[str] = Field(None, description="Frequency of interest payments.")
    basis: Optional[str] = Field(None, description="Benchmark rate used for floating interest (e.g. LIBOR, EURIBOR). ")
    spread: Optional[float] = Field(None, description="Spread added to the base rate (basis) for floating rates. ")

class FinancialInstrumentIdentification(BaseModel):
    """
    Financial instrument identification in the form of a key–value pair (identifier + type).

    """
    identifier: str = Field(..., description="Instrument identification string.")
    type: str = Field(..., description="Type of instrument identifier (ISIN preferred, but other schemes are possible). ")

class CfiCode(RootModel):
    """
    Classification of financial instrument (CFI) code according to ISO 10962. At least the CFI Category (1st char) and Group (2nd char) must be present.

    """
    root: str

class Quantity(BaseModel):
    """
    Quantity representation (unit, face amount, amortised value, token units).
    """
    type: str = Field(..., description="Type of the quantity.")
    value: float = Field(..., description="Signed decimal amount.")

class AssetClass(BaseModel):
    """
    Asset class definition used for portfolio classification and reporting.
    """
    assetClassId: Optional[str] = Field(None, description="Unique identifier for the asset class record.")
    displayName: Optional[str] = Field(None, description="Human-readable name shown in reports.")
    parentClassId: Optional[str] = Field(None, description="Identifier of the parent asset class used for roll-ups.")
    liquidityDays: Optional[int] = Field(None, description="Standard settlement or liquidity horizon in days.")
    valuationFrequency: Optional[str] = Field(None, description="Frequency at which the asset class is valued.")
    baseCurrency: Optional[Currency] = Field(None, description="Base currency used for risk and performance calculations.")
    isRiskFree: Optional[bool] = Field(None, description="Indicates whether the asset class is treated as risk-free for ratios.")
    expectedReturn: Optional[float] = Field(None, description="Expected annual return assumption for the asset class.")
    standardDeviation: Optional[float] = Field(None, description="Expected volatility assumption for the asset class.")
    primaryReturnDriver: Optional[str] = Field(None, description="Primary return driver for the asset class (e.g., growth, income).")
    incomeLogic: Optional[str] = Field(None, description="Income recognition behavior for the asset class.")
    correlationMatrix: Optional[List[CorrelationEntry]] = Field(None, description="Correlation entries against other asset classes.")
    mappingRules: Optional[List[AssetClassMappingRule]] = Field(None, description="Rule set used to classify instruments into this asset class.")
    valuationLogic: Optional[str] = Field(None, description="Valuation approach or pricer used for this asset class.")
    riskWeight: Optional[float] = Field(None, description="Risk weight applied in compliance or capital calculations.")
    taxStatus: Optional[str] = Field(None, description="Tax treatment category for the asset class.")
    primaryIncomeTax: Optional[str] = Field(None, description="Primary income tax characterization applied to the asset class.")
    capitalGainsTax: Optional[str] = Field(None, description="Capital gains tax characterization applied to the asset class.")
    allowShorting: Optional[bool] = Field(None, description="Indicates whether short positions are allowed for the asset class.")
    defaultBenchmark: Optional[str] = Field(None, description="Default benchmark identifier used for performance attribution.")
    hybridAttributes: Optional[HybridAttributes] = Field(None, description="Optional hybrid-specific attributes (e.g., convertibles).")

class AssetClassMappingRule(BaseModel):
    """
    Rule used to classify instruments into an asset class.
    """
    cfiPrefix: Optional[str] = Field(None, description="CFI prefix used to map instruments into this asset class.")
    countryCode: Optional[Country] = Field(None, description="ISO country code used for regional mapping rules.")
    maturityDaysMax: Optional[int] = Field(None, description="Maximum maturity in days for the rule to apply.")
    requiredInstrumentType: Optional[str] = Field(None, description="Instrument type filter for the classification rule.")
    assetClassLabel: Optional[str] = Field(None, description="Asset class label assigned when the rule matches.")

class CorrelationEntry(BaseModel):
    """
    Correlation between this asset class and another asset class.
    """
    relatedAssetClassId: Optional[str] = Field(None, description="Identifier of the related asset class.")
    correlation: Optional[float] = Field(None, description="Correlation coefficient with the related asset class.")

class HybridAttributes(BaseModel):
    """
    Attributes specific to hybrid instruments like convertibles.
    """
    conversionRatio: Optional[float] = Field(None, description="Number of shares received per bond upon conversion.")
    strikePrice: Optional[CurrencyAmount] = Field(None, description="Price at which conversion becomes optimal.")
    delta: Optional[float] = Field(None, description="Sensitivity of the hybrid value to the underlying equity price.")
    bondFloor: Optional[CurrencyAmount] = Field(None, description="Theoretical bond value without the conversion option.")

class BasketDefinition(BaseModel):
    """
    The header structure defining a collection of assets.

    """
    basketId: Optional[str] = Field(None, description="Unique identifier for the basket definition.")
    basketType: Optional[str] = Field(None, description="The mathematical logic used to calculate the basket's performance.")
    currency: Optional[Currency] = Field(None, description="The base currency of the basket.")
    rebalancingType: Optional[str] = Field(None, description="Indicates if components are fixed or updated periodically.")
    constituentCount: Optional[int] = Field(None, description="Total number of assets currently in the basket.")
    constituents: Optional[List[BasketConstituent]] = Field(None, description="List of individual assets within the basket.")
    correlationMatrix: Optional[List[CorrelationEntry]] = Field(None, description="Matrix defining the statistical relationships between basket members.")

class BasketConstituent(BaseModel):
    """
    An individual asset within a basket, including its reference fixing and weight.

    """
    underlyingInstrument: Optional[FinancialInstrument] = Field(None, description="The financial instrument or index that this constituent represents.")
    initialFixing: Optional[Price] = Field(None, description="The reference price of the asset at the start of the contract.")
    weight: Optional[Decimal] = Field(None, description="The percentage weight of this asset in the basket (e.g., 0.33 for 33%).")
    barrierLevel: Optional[Price] = Field(None, description="The price threshold for this component, often used in structured products.")
    currentPerformance: Optional[Decimal] = Field(None, description="The relative performance calculated as (Current Price / Initial Fixing).")
    isQuanto: Optional[bool] = Field(None, description="Indicates if the constituent is currency-shielded (Quanto).")

class Instrument(BaseModel):
    """
    Venue-independent representation of a financial instrument (security master).

    """
    isin: Optional[str] = None
    figi: Optional[str] = None
    cfiCode: Optional[CfiCode] = None
    instrumentType: Optional[str] = None
    currency: Optional[str] = None
    issuer: Optional[Any] = None
    listings: Optional[List[Any]] = None

class Listing(BaseModel):
    """
    A listing is the admission of an Instrument to trading on a specific trading venue. It contains static venue-specific attributes only.

    """
    listingId: Optional[str] = None
    instrument: Optional[Any] = None
    venue: Optional[Any] = None
    mic: Optional[str] = None
    ticker: Optional[str] = Field(None, description="Venue-specific trading symbol.")
    listingCurrency: Optional[str] = None
    marketSegment: Optional[str] = None
    firstTradingDate: Optional[Any] = None
    lotSize: Optional[int] = None
    tickSizeTable: Optional[str] = None
    status: Optional[str] = None

class TradingVenue(BaseModel):
    """
    A trading venue such as an exchange or MTF.

    """
    mic: Optional[str] = None
    name: Optional[str] = None
    country: Optional[Country] = None
    venueType: Optional[str] = None
    timezone: Optional[str] = None
    operator: Optional[str] = None

class MarketDataSnapshot(BaseModel):
    """
    End-of-day or periodic snapshot of market data for a specific listing. Represents dynamic values at a timestamp (not historical stream).

    """
    snapshotId: Optional[str] = None
    listing: Optional[Any] = None
    timestamp: Optional[Any] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    last: Optional[float] = None
    volume: Optional[float] = None
    turnover: Optional[float] = None
    vwap: Optional[float] = None

class MarketDataStream(BaseModel):
    """
    Real-time or intraday tick data stream for quotes and trades. This entity can be used to store historical ticks or to reference an external feed.

    """
    eventId: Optional[str] = None
    listing: Optional[Any] = None
    timestamp: Optional[Any] = None
    eventType: Optional[str] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    bidSize: Optional[float] = None
    askSize: Optional[float] = None
    lastPrice: Optional[float] = None
    lastSize: Optional[float] = None
    tradeConditions: Optional[List[str]] = None

class OrderBook(BaseModel):
    """
    Snapshot of the order book for a given listing at a precise timestamp. Supports Level I and Level II data.

    """
    orderbookId: Optional[str] = None
    listing: Optional[Any] = None
    timestamp: Optional[Any] = None
    bids: Optional[List[Any]] = None
    asks: Optional[List[Any]] = None

class OrderBookLevel(BaseModel):
    """
    Represents a price level in the order book.

    """
    price: Optional[float] = None
    size: Optional[float] = None
    level: Optional[int] = Field(None, description="Price-depth level (1 = best bid/ask)")

class TradingVenueStandardInfo(BaseModel):
    """
    Information about the ISO 10383 standard.
    """
    name: Optional[str] = Field(None, description="Market Identifier Codes (MIC).")
    isoStandard: Optional[str] = Field(None, description="ISO 10383.")
    authority: Optional[str] = Field(None, description="International Organization for Standardization (ISO).")

class User(BaseModel):
    """
    Staff user entry in the bank address book.
    """
    userId: Optional[str] = Field(None, description="Unique identifier of the user.")
    fullName: Optional[str] = Field(None, description="Full name of the user.")
    email: Optional[str] = Field(None, description="Email address of the user.")
    phone: Optional[str] = Field(None, description="Phone number for the user.")
    jobTitle: Optional[str] = Field(None, description="Job title or raw_data held by the user.")
    isActive: Optional[bool] = Field(None, description="Indicates whether the user is currently active.")
    organizationUnit: Optional[OrganizationUnit] = Field(None, description="Organizational unit the user belongs to.")
    substituteUserId: Optional[str] = Field(None, description="Identifier of a substitute user for temporary handover.")
    assignments: Optional[List[Assignment]] = Field(None, description="Portfolio or client assignments that define functional roles.")

class OrganizationUnit(BaseModel):
    """
    Organizational unit in the bank hierarchy.
    """
    unitId: Optional[str] = Field(None, description="Unique identifier of the organizational unit.")
    name: Optional[str] = Field(None, description="Name of the organizational unit.")
    unitType: Optional[str] = Field(None, description="Unit type such as branch, team, division, or region.")
    parentUnit: Optional[OrganizationUnit] = Field(None, description="Parent organizational unit in the hierarchy.")

class Role(BaseModel):
    """
    Functional role that defines a permission set.
    """
    roleId: Optional[str] = Field(None, description="Unique identifier of the role.")
    roleName: Optional[str] = Field(None, description="Human-readable name of the role.")
    permissions: Optional[List[str]] = Field(None, description="List of permissions granted by the role.")
    permissionMask: Optional[str] = Field(None, description="Optional encoded mask representing permissions.")

class Assignment(BaseModel):
    """
    Assignment linking a user to a portfolio with a role and validity period.
    """
    assignmentId: Optional[str] = Field(None, description="Unique identifier of the assignment.")
    user: Optional[User] = Field(None, description="User assigned to the portfolio.")
    portfolio: Optional[PortfolioInformation] = Field(None, description="Portfolio that the assignment applies to.")
    role: Optional[Role] = Field(None, description="Role assigned for this portfolio.")
    validFrom: Optional[date] = Field(None, description="Start date of the assignment validity.")
    validTo: Optional[date] = Field(None, description="End date of the assignment validity.")
    isPrimaryAdvisor: Optional[bool] = Field(None, description="Indicates whether the user is the primary advisor.")

class PartnerType(str, Enum):
    """
    Type of the partner (e.g., natural person, legal entity).
    """
    natural_person = "natural_person"
    legal_entity = "legal_entity"
    advisory_unit = "advisory_unit"

class PartnerStatus(str, Enum):
    """
    Status of the partner in the system.
    """
    active = "active"
    inactive = "inactive"
    prospect = "prospect"

class Gender(str, Enum):
    """
    Gender of a natural person.
    """
    male = "male"
    female = "female"
    other = "other"
    unknown = "unknown"

class Language(RootModel):
    """
    ISO 639-1 language code.
    """
    root: str

class Date(RootModel):
    """
    Date according to ISO 8601 (YYYY-MM-DD).
    """
    root: date

class Boolean(RootModel):
    """
    Boolean value.
    """
    root: bool

class ShortText(RootModel):
    """
    A short string of text.
    """
    root: str

class LongText(RootModel):
    """
    A longer string of text.
    """
    root: str

class EmailAddress(RootModel):
    """
    Email address.
    """
    root: str

class PhoneNumber(RootModel):
    """
    Phone number in international format.
    """
    root: str

class RiskAbility(RootModel):
    """
    Risk ability level.
    """
    root: str

class RiskTolerance(RootModel):
    """
    Risk tolerance level.
    """
    root: str

class ContactType(str, Enum):
    """
    Type of communication channel.
    """
    phone = "phone"
    email = "email"
    fax = "fax"
    mobile = "mobile"
    mail = "mail"

class Segment(RootModel):
    """
    Customer segment.
    """
    root: str

class PartnerRiskRating(RootModel):
    """
    Internal partner risk rating (KYC / counterparty risk). Distinct from the credit Rating object in `rating/credit_rating/CreditRating.yml` which carries agency, notation, outlook and dates.

    """
    root: str

class Partner(BaseModel):
    """
    Base entity for all types of partners (natural, legal, advisory unit).
    """
    partnerId: Optional[str] = Field(None, description="Unique identifier for the partner.")
    partnerInternalId: Optional[str] = Field(None, description="Internal system identifier for the partner.")
    externalIds: Optional[List[str]] = Field(None, description="External identifiers for the partner.")
    partnerType: Optional[PartnerType] = Field(None, description="The type of partner.")
    primaryName: Optional[str] = Field(None, description="Primary name of the partner.")
    country: Optional[Country] = Field(None, description="Home country of the partner.")
    legalResidence: Optional[Country] = Field(None, description="Legal residence of the partner.")
    preferredLanguage: Optional[Language] = Field(None, description="Preferred language for communication.")
    preferredReferenceCurrency: Optional[Currency] = Field(None, description="Preferred currency for reports and valuations.")
    companyIdentifier: Optional[str] = Field(None, description="Identifier for the company (if applicable).")
    advisors: Optional[List[AdvisoryUnit]] = Field(None, description="Advisors associated with this partner.")
    partnerFlags: Optional[List[str]] = Field(None, description="Flags associated with the partner.")
    partnerStatus: Optional[PartnerStatus] = Field(None, description="Current status of the partner.")
    partnerDetails: Optional[PartnerDetails] = Field(None, description="Detailed information about the partner.")

class NaturalPerson(Partner):
    """
    A partner who is a natural person.
    """
    firstName: Optional[str] = Field(None, description="First name of the person.")
    lastName: Optional[str] = Field(None, description="Last name of the person.")
    title: Optional[str] = Field(None, description="Academic or professional title.")
    salutation: Optional[str] = Field(None, description="Salutation (e.g., Mr., Ms.).")
    suffix: Optional[str] = Field(None, description="Name suffix.")
    gender: Optional[Gender] = Field(None, description="Gender of the person.")
    birthDate: Optional[date] = Field(None, description="Date of birth.")
    nationality: Optional[Country] = Field(None, description="Nationality of the person.")
    countryOfBirth: Optional[Country] = Field(None, description="Country where the person was born.")

class LegalPartner(Partner):
    """
    A partner who is a legal entity.
    """
    organizationName: Optional[str] = Field(None, description="Name of the organization.")
    organizationType: Optional[str] = Field(None, description="Type of the organization.")
    legalForm: Optional[str] = Field(None, description="Legal form of the entity (e.g., AG, GmbH).")

class AdvisoryUnit(Partner):
    """
    An entity representing an advisory team or person.
    """
    associationName: Optional[str] = Field(None, description="Name of the advisory association.")
    associationType: Optional[str] = Field(None, description="Type of advisory association.")

class PartnerDetails(BaseModel):
    """
    Detailed attributes of a partner.
    """
    communicationChannels: Optional[List[CommunicationChannel]] = Field(None, description="List of communication channels.")
    categorization: Optional[Categorization] = Field(None, description="Partner categorization.")
    customerAttributes: Optional[CustomerAttributes] = Field(None, description="Additional customer attributes.")
    regulatory: Optional[Regulatory] = Field(None, description="Regulatory information.")

class Categorization(BaseModel):
    """
    Categorization details for a partner.
    """
    partnerSegment: Optional[Segment] = Field(None, description="Main segment of the partner.")
    partnerSegmentGroup: Optional[str] = Field(None, description="Segment group.")
    partnerRating: Optional[Rating] = Field(None, description="Internal or external rating.")
    riskTolerance: Optional[RiskTolerance] = Field(None, description="Risk tolerance.")
    riskAbility: Optional[RiskAbility] = Field(None, description="Risk ability.")

class CustomerAttributes(BaseModel):
    """
    Custom attributes for the partner.
    """
    occupation: Optional[str] = Field(None, description="Occupation of the partner.")
    employer: Optional[str] = Field(None, description="Employer of the partner.")

class Regulatory(BaseModel):
    """
    Regulatory compliance information.
    """
    mifid: Optional[MIFID] = Field(None, description="MiFID related information.")
    fidleg: Optional[FIDLEG] = Field(None, description="FIDLEG related information.")
    taxes: Optional[Taxes] = Field(None, description="Tax related information.")
    fatca: Optional[FATCA] = Field(None, description="FATCA status.")
    qi: Optional[QI] = Field(None, description="Qualified Intermediary status.")

class MIFID(BaseModel):
    """
    MiFID classification.
    """
    category: Optional[str] = Field(None, description="MiFID category.")
    investorType: Optional[str] = Field(None, description="Type of investor.")

class FIDLEG(BaseModel):
    """
    FIDLEG classification (Swiss regulation).
    """
    category: Optional[str] = Field(None, description="FIDLEG category.")
    investorType: Optional[str] = Field(None, description="Type of investor.")

class Taxes(BaseModel):
    """
    Tax residency and related info.
    """
    taxCountry: Optional[Country] = Field(None, description="Primary tax country.")
    taxStayType: Optional[str] = Field(None, description="Type of tax stay.")

class FATCA(BaseModel):
    """
    FATCA compliance status.
    """
    status: Optional[str] = Field(None, description="FATCA status.")
    document: Optional[str] = Field(None, description="Reference to FATCA document.")

class QI(BaseModel):
    """
    Qualified Intermediary status.
    """
    status: Optional[str] = Field(None, description="QI status.")
    document: Optional[str] = Field(None, description="Reference to QI document.")

class CommunicationChannel(BaseModel):
    """
    Base for communication channels.
    """
    type: Optional[ContactType] = Field(None, description="Type of channel.")
    value: Optional[str] = Field(None, description="The actual address or number.")
    priority: Optional[int] = Field(None, description="Priority of this channel.")

class Phone(CommunicationChannel):
    """
    Phone communication channel.
    """
    phoneNumber: Optional[PhoneNumber] = Field(None, description="The phone number.")

class Email(CommunicationChannel):
    """
    Email communication channel.
    """
    emailAddress: Optional[EmailAddress] = Field(None, description="The email address.")

class Fax(CommunicationChannel):
    """
    Fax communication channel.
    """
    faxNumber: Optional[PhoneNumber] = Field(None, description="The fax number.")

class TeamAdvisor(AdvisoryUnit):
    """
    An advisory team.
    """
    teamId: Optional[str] = Field(None, description="Identifier for the team.")
    teamName: Optional[str] = Field(None, description="Name of the team.")

class PersonAdvisor(AdvisoryUnit):
    """
    An individual advisor.
    """
    advisorId: Optional[str] = Field(None, description="Identifier for the advisor.")
    firstName: Optional[str] = Field(None, description="First name of the advisor.")
    lastName: Optional[str] = Field(None, description="Last name of the advisor.")
    role: Optional[Role] = Field(None, description="Role of the advisor.")

class IssuanceRecord(BaseModel):
    """
    The central record for a security's birth, linking the legal entity (Issuer) to the instrument definition and the primary market event.

    """
    id: Optional[str] = Field(None, description="Unique identifier for the issuance record.")
    status: Optional[IssuanceStatus] = Field(None, description="The current state of the issuance in its lifecycle.")
    issuer: Optional[Issuer] = Field(None, description="The legal entity that is issuing the instrument.")
    instrument: Optional[FinancialInstrument] = Field(None, description="The static security definition of the issued instrument.")
    primaryMarketEvent: Optional[PrimaryMarketEvent] = Field(None, description="Details of the issuance in the primary market.")
    secondaryMarketConfig: Optional[SecondaryMarketConfig] = Field(None, description="Configuration and linkage for secondary market trading.")

class IssuanceStatus(str, Enum):
    """
    The lifecycle state of a security issuance.
    """
    proposed = "proposed"
    book_building = "book_building"
    active = "active"
    matured = "matured"
    redeemed = "redeemed"
    cancelled = "cancelled"

class PrimaryMarketEvent(BaseModel):
    """
    Metadata tracking the issuance function in the primary market.
    """
    announcementDate: Optional[date] = Field(None, description="When the market is first informed about the issuance.")
    issueDate: Optional[date] = Field(None, description="The official \"birthday\" of the security.")
    datedDate: Optional[date] = Field(None, description="When interest begins to accrue (relevant for fixed income).")
    offeringPrice: Optional[Price] = Field(None, description="The \"Book Price\" set by the underwriter in the primary market.")
    totalAuthorizedAmount: Optional[CurrencyAmount] = Field(None, description="Total authorized value of the issuance.")
    totalAuthorizedQuantity: Optional[Quantity] = Field(None, description="Total authorized shares or units.")
    underwritingSyndicate: Optional[UnderwritingSyndicate] = Field(None, description="Details of the firms managing the issuance.")

class UnderwritingSyndicate(BaseModel):
    """
    Information about the lead and co-managers of the issuance.
    """
    leadManager: Optional[str] = Field(None, description="The primary financial institution managing the issuance.")
    coManagers: Optional[List[str]] = Field(None, description="List of additional financial institutions in the syndicate.")
    underwritingFeeBps: Optional[int] = Field(None, description="Fees expressed in basis points (1/100th of a percent) to avoid precision errors.")

class SecondaryMarketConfig(BaseModel):
    """
    External data hooks and configuration for secondary market trading.
    """
    primaryExchange: Optional[str] = Field(None, description="The main exchange where the security is traded.")
    marketMakerIds: Optional[List[str]] = Field(None, description="Identifiers for institutions providing liquidity.")
    liquidityScore: Optional[str] = Field(None, description="Assessment of the security's liquidity (e.g., HIGH, MEDIUM, LOW).")
    pricingSource: Optional[str] = Field(None, description="Preferred source for market data (e.g., BLOOMBERG, REFINITIV).")

class CommonErrorType(str, Enum):
    """
    Error Types for CommonErrorResponse.
    """
    problems_invalid_payload = "/problems/invalid_payload"
    problems_malformed_payload = "/problems/malformed_payload"
    problems_invalid_token = "/problems/invalid_token"
    problems_expired_token = "/problems/expired_token"
    problems_insufficient_privileges = "/problems/insufficient_privileges"
    problems_no_access_to_resource = "/problems/no_access_to_resource"
    problems_resource_does_not_exist = "/problems/resource_does_not_exist"
    problems_resource_not_ready = "/problems/resource_not_ready"
    problems_resource_too_large = "/problems/resource_too_large"
    problems_wrong_method = "/problems/wrong_method"
    problems_operation_not_allowed = "/problems/operation_not_allowed"
    problems_technical_error = "/problems/technical_error"
    problems_not_implemented = "/problems/not_implemented"
    problems_service_unavailable = "/problems/service_unavailable"

class CommonErrorResponse(BaseModel):
    """
    Common error response.
    """
    type: Optional[CommonErrorType] = Field(None, description="Type of the error.")
    title: Optional[str] = Field(None, description="Title of the error response.")
    detail: Optional[str] = Field(None, description="Detailed description of the error response.")
    instance: Optional[str] = Field(None, description="Entity instance that threw the error.")

class Customer(BaseModel):
    """
    Overview of the customer with the respective accounts.
    """
    id: Optional[str] = Field(None, description="Unique and unambiguous identification (i.e. UUID) used by the bank for the customer.")
    number: Optional[str] = Field(None, description="Contains the customers custody proprietary customer number if available.")
    referenceCurrency: Optional[Currency] = Field(None, description="Reference currency for the customer.")

class Position(BaseModel):
    """
    Position entity.
    """
    id: Optional[str] = Field(None, description="Identification for the raw_data given by the bank.")
    financialInstrument: Optional[FinancialInstrument] = Field(None, description="Financial instrument held in this raw_data.")
    account: Optional[Account] = Field(None, description="Account in which the raw_data is held.")
    name: Optional[str] = Field(None, description="Name of the raw_data.")
    currency: Optional[Currency] = Field(None, description="Currency of the raw_data.")
    safekeepingPlace: Optional[str] = Field(None, description="BIC of the place where the securities are safe-kept, physically or notionally.")
    additionalCustodianInformation: Optional[str] = Field(None, description="Used for special use cases where safekeepingPlace is not sufficient. BIC of the place where the securities are safe-kept, physically or notionally.")
    additionalDetails: Optional[str] = Field(None, description="Provides additional information on the raw_data.")

class Valuation(BaseModel):
    """
    Detailed information about the valuation of a raw_data.
    """
    valueInPositionCurrency: Optional[CurrencyAmount] = Field(None, description="Value of the raw_data in its original currency.")
    valueInReferenceCurrency: Optional[CurrencyAmount] = Field(None, description="Value of the raw_data in the reference currency.")
    valuationDate: Optional[date] = Field(None, description="Date when the raw_data was valuated.")

class ValuationPrice(BaseModel):
    """
    Price entity with type, numeric value, and optional currency.
    """
    type: Optional[str] = Field(None, description="Indicates whether the price is an actual currency amount per unit or a percentage.")
    value: Optional[float] = Field(None, description="Signed decimal price value.")
    currency: Optional[Currency] = Field(None, description="Currency of the price.")
    valuationDate: Optional[date] = Field(None, description="Date of the valuation price.")
    priceType: Optional[str] = Field(None, description="Indicates which type of price is used.")

class ForeignExchangeRate(BaseModel):
    """
    Foreign exchange rate between two currencies.
    """
    unitCurrency: Optional[Currency] = Field(None, description="Currency of the unit.")
    quotedCurrency: Optional[Currency] = Field(None, description="Currency in which the rate is quoted.")
    rate: Optional[float] = Field(None, description="FX rate.")

class ValuationForeignExchangeRate(BaseModel):
    """
    Foreign exchange rate entity used for valuation.
    """
    unitCurrency: Optional[Currency] = Field(None, description="Currency of the unit.")
    quotedCurrency: Optional[Currency] = Field(None, description="Currency in which the rate is quoted.")
    rate: Optional[float] = Field(None, description="FX rate.")
    valuationDate: Optional[date] = Field(None, description="Date of the valuation FX rate.")

class ValuatedPosition(Position):
    """
    Valuated raw_data entity.
    """
    endOfDayIndicator: Optional[bool] = Field(None, description="Indicates whether this is an end-of-day valuation.")
    positionDate: Optional[date] = Field(None, description="Valuation date of the raw_data.")
    quantity: Optional[Quantity] = Field(None, description="Quantity of the financial instrument held.")
    valuation: Optional[Valuation] = Field(None, description="Market valuation of the raw_data.")
    price: Optional[ValuationPrice] = Field(None, description="Market price used for valuation.")
    foreignExchangeRate: Optional[ValuationForeignExchangeRate] = Field(None, description="FX rate used to convert the valuation into the portfolio currency.")
    costPrice: Optional[Price] = Field(None, description="Cost price of the raw_data.")
    costForeignExchangeRate: Optional[ForeignExchangeRate] = Field(None, description="FX rate used for cost conversion.")
    accruedInterest: Optional[CurrencyAmount] = Field(None, description="Accrued interest (for interest-bearing instruments).")
    numberOfDaysAccrued: Optional[int] = Field(None, description="Number of days of accrued interest.")
    blockedQuantity: Optional[Quantity] = Field(None, description="Quantity that is blocked or unavailable.")

class PortfolioInformation(BaseModel):
    """
    Information about the portfolio.
    """
    identification: Optional[str] = Field(None, description="Unique and unambiguous identification for the portfolio between the portfolio owner and the portfolio servicer.")
    referenceCurrency: Optional[Currency] = Field(None, description="Reference currency for the portfolio.")

class Account(BaseModel):
    """
    Account entity.
    """
    id: Optional[str] = Field(None, description="Unique and unambiguous identification for the account. The IBAN should NOT be the account identifier.")
    type: Optional[str] = Field(None, description="Indicates the type of the account.")
    name: Optional[str] = Field(None, description="Name of the account. It provides an additional means of identification, and is designated by the account servicer in agreement with the account owner.")
    referenceCurrency: Optional[Currency] = Field(None, description="Reference currency for the account.")
    iban: Optional[str] = Field(None, description="Contains the accounts International Banking Account Number (IBAN) for an account if available.")
    number: Optional[str] = Field(None, description="Contains the accounts custody proprietary account number for an account if available.")
    designation: Optional[str] = Field(None, description="Supplementary information on the account. Designated by the account servicer.")
    portfolioInformation: Optional[PortfolioInformation] = Field(None, description="Information about the portfolio the account belongs to.")

class TransactionType(str, Enum):
    """
    Type of the transaction.
    """
    buy = "buy"
    sell = "sell"
    dividend = "dividend"
    interest = "interest"
    fee = "fee"
    tax = "tax"
    transfer_in = "transfer_in"
    transfer_out = "transfer_out"
    corporate_action = "corporate_action"
    other = "other"

class PlaceOfTrade(BaseModel):
    """
    Place where the trade was executed.
    """
    type: Optional[str] = Field(None, description="Type of the place of trade.")
    value: Optional[str] = Field(None, description="Value of the place of trade.")

class MovementType(str, Enum):
    """
    Indicates if the movement is a credit or a debit.
    """
    credit = "credit"
    debit = "debit"

class Movement(BaseModel):
    """
    Movement entity.
    """
    type: Optional[MovementType] = Field(None, description="Type of the movement.")
    quantity: Optional[Quantity] = Field(None, description="Quantity of the movement.")
    account: Optional[Account] = Field(None, description="Account of the movement.")
    financialInstrument: Optional[FinancialInstrument] = Field(None, description="Financial instrument of the movement.")

class PostingAmount(BaseModel):
    """
    Posting amount entity.
    """
    type: Optional[str] = Field(None, description="Type of the posting amount.")
    amount: Optional[CurrencyAmount] = Field(None, description="Amount of the posting.")

class Transaction(BaseModel):
    """
    Transaction entity.
    """
    id: Optional[str] = Field(None, description="Unique transaction identifier.")
    type: Optional[TransactionType] = Field(None, description="Type of the transaction.")
    transactionDate: Optional[date] = Field(None, description="Date on which the transaction was booked.")
    customerId: Optional[str] = Field(None, description="Customer (business partner) identifier.")
    reversalIndicator: Optional[bool] = Field(None, description="Indicates whether this transaction is a reversal.")
    endOfDayIndicator: Optional[bool] = Field(None, description="Indicates whether this transaction is an end-of-day booking.")
    reference: Optional[str] = Field(None, description="Bank reference or transaction reference.")
    description: Optional[str] = Field(None, description="Human-readable transaction description.")
    placeOfTrade: Optional[PlaceOfTrade] = Field(None, description="Trading venue or market where the transaction occurred.")
    reversedTransactionId: Optional[str] = Field(None, description="Reference to the transaction that was reversed.")
    tradeDate: Optional[date] = Field(None, description="Trade execution date.")
    settlementDate: Optional[date] = Field(None, description="Settlement (value) date.")
    triggeringFinancialInstrument: Optional[FinancialInstrument] = Field(None, description="Instrument that triggered the transaction.")
    triggeringQuantity: Optional[Quantity] = Field(None, description="Quantity of the instrument involved.")
    triggeringPrice: Optional[Price] = Field(None, description="Price at which the instrument was traded.")
    movementList: Optional[List[Movement]] = Field(None, description="List of security or cash movements generated by the transaction.")
    postingAmountList: Optional[List[PostingAmount]] = Field(None, description="List of posted amounts resulting from the transaction.")
    settlementCurrency: Optional[Currency] = Field(None, description="Currency in which settlement took place.")
    additionalDetails: Optional[str] = Field(None, description="Free-text additional transaction information.")

class Index(BaseModel):
    """
    Reference index (benchmark, market index).
    """
    pass

class OverlayProgram(BaseModel):
    """
    The strategic layer applied to a portfolio. It represents the collective  synthetic positions and rules of an overlay strategy.

    """
    programId: Optional[str] = Field(None, description="Unique identifier for the overlay program.")
    notionalExposure: Optional[CurrencyAmount] = Field(None, description="The total market value controlled by the overlay derivatives.")
    marketValue: Optional[CurrencyAmount] = Field(None, description="The current liquidation value of the overlay positions (often near zero at inception).")
    variationMargin: Optional[CurrencyAmount] = Field(None, description="The daily cash flow moving in/out due to price changes.")
    targetPortfolio: Optional[BasePortfolio] = Field(None, description="The underlying \"physical\" assets that this overlay is covering or enhancing.")
    instruments: Optional[List[FinancialInstrument]] = Field(None, description="The derivative tools (Futures, Forwards, Options, Swaps) used to execute the overlay.")
    constraints: Optional[List[PolicyConstraint]] = Field(None, description="Risk mandates and limits governing the program.")

class BasePortfolio(BaseModel):
    """
    The underlying physical assets (Equities, Bonds, etc.) targeted by an overlay.
    """
    portfolioId: Optional[str] = Field(None, description="Unique identifier for the base portfolio.")
    marketValue: Optional[CurrencyAmount] = Field(None, description="Total market value of the physical holdings.")
    baseCurrency: Optional[Currency] = Field(None, description="The primary currency of the portfolio.")

class PolicyConstraint(BaseModel):
    """
    Regulatory or internal rules governing the overlay strategy.
    """
    constraintType: Optional[str] = Field(None, description="The category of the constraint.")
    limitValue: Optional[float] = Field(None, description="The numeric threshold for the limit.")
    description: Optional[str] = Field(None, description="Natural language description of the rule.")

class CurrencyOverlay(OverlayProgram):
    """
    Strategy used to offset currency risk or bet on exchange rates.
    """
    hedgingCurrency: Optional[Currency] = Field(None, description="The target currency into which exposures are being hedged.")
    hedgeRatio: Optional[float] = Field(None, description="The percentage of exposure that is hedged (e.g., 1.0 for 100%).")

class RebalancingOverlay(OverlayProgram):
    """
    Strategy using futures to nudge portfolio exposure back to target allocations.
    """
    pass

class RiskOverlay(OverlayProgram):
    """
    Strategy (like Put options) acting as an insurance policy against market crashes.
    """
    pass

class TacticalAssetAllocation(OverlayProgram):
    """
    Short-term strategic shifts in exposure (e.g., adding gold for a limited period).
    """
    pass

class InterestRateOverlay(OverlayProgram):
    """
    Strategy using swaps or caps to protect against interest rate movements.
    """
    pass

class MarketNeutralOverlay(OverlayProgram):
    """
    Strategy aimed at eliminating market direction risk.
    """
    pass

class VolatilityOverlay(OverlayProgram):
    """
    Strategy using options to hedge against sudden volatility drops or spikes.
    """
    pass

class SectorRotationOverlay(OverlayProgram):
    """
    Strategy to dynamically rotate portfolio weights across sectors.
    """
    pass

class CommodityOverlay(OverlayProgram):
    """
    Strategy to gain exposure to commodities without physical delivery.
    """
    pass

class CreditOverlay(OverlayProgram):
    """
    Strategy (like CDS) to protect against default risk in high-yield bonds.
    """
    pass

class EventDrivenOverlay(OverlayProgram):
    """
    Strategy to capitalize on price movements from major corporate events.
    """
    pass

class IndustrySector(BaseModel):
    """
    Container for one or more time-versioned industry/sector classification assignments.
Normative rules: - Only DIRECT assignments are stored here (no inherited/materialized assignments). - Issuer and Instrument assignments are independent and may differ. - Override convention for consumers: when computing an instrument’s effective
  classification, prefer Instrument assignments; if none exist, fall back to Issuer
  assignments (do not duplicate Issuer assignments onto the Instrument).

    """
    gics: Optional[GicsClassification] = Field(None, description="Optional GICS classification for the issuer or instrument.")
    icb: Optional[IcbClassification] = Field(None, description="Optional ICB classification for the issuer or instrument.")
    telekurs: Optional[TelekursClassification] = Field(None, description="Optional Telekurs classification for the issuer or instrument.")
    canonical: Optional[List[ClassificationAssignment]] = Field(None, description="Optional canonical classification assignments (typically to Issuer or Instrument). Each assignment points to a system and terminal node and can be time-versioned. Normative rule: - Each item MUST target the owning entity instance via applies_to   (direct assignment only). ")
    sectorLabel: Optional[str] = Field(None, description="Free-form sector label sourced from a non-canonical taxonomy (e.g., yfinance's \"Consumer Defensive\" / \"Technology\"). Use the structured `gics` / `icb` / `telekurs` / `canonical` fields when a registered classification system is available. This field exists so providers that only expose plain English labels can still populate the panel — without burning a classification system on every Yahoo row. ")
    industryLabel: Optional[str] = Field(None, description="Free-form industry label, peer of `sectorLabel`. Same rationale: preserves the provider's plain-English categorisation when no registered industry code is on hand. ")
    source: Optional[str] = Field(None, description="Where `sectorLabel` / `industryLabel` came from (e.g., `yfinance`). The structured classification fields above carry their own provenance via their own enclosing entities, but free-form labels need this field to stay traceable. ")

class Issuer(BaseModel):
    """
    The legal entity responsible for issuing a financial instrument.
    """
    id: Optional[str] = Field(None, description="Unique identifier for the issuer.")
    issuerCategory: Optional[str] = Field(None, description="Category of the entity (e.g., Issuer).")
    identifiers: Optional[List[IssuerIdentifier]] = Field(None, description="List of identifiers for the issuer (e.g., LEI).")
    legalIdentity: Optional[LegalIdentity] = Field(None, description="Legal identity details of the issuer.")
    corporateHierarchy: Optional[CorporateHierarchy] = Field(None, description="Corporate hierarchy details.")
    regulatoryRoles: Optional[List[str]] = Field(None, description="List of regulatory roles (e.g., issuer, counterparty).")
    metadata: Optional[IssuerMetadata] = Field(None, description="Metadata about the issuer record.")
    issuerName: Optional[str] = Field(None, description="Name of the issuer.")
    issuerType: Optional[str] = Field(None, description="Classification of the issuer type.")
    domicileRegion: Optional[str] = Field(None, description="Link to the Geography semantic taxonomy.")
    regulator: Optional[str] = Field(None, description="Supervisory authority overseeing this issuer.")
    creditProfile: Optional[CreditProfile] = Field(None, description="Creditworthiness profile of the issuer.")
    esgProfile: Optional[ESGProfile] = Field(None, description="ESG profile of the issuer.")
    incorporationDate: Optional[date] = Field(None, description="Date of incorporation.")
    industrySector: Optional[IndustrySector] = Field(None, description="Industry/sector classification assignments for this issuer (e.g., GICS, ICB, Telekurs, or bank-specific systems) represented in canonical form. ")

class IssuerIdentifier(BaseModel):
    """
    Formal identification of the legal entity.
    """
    id: Optional[str] = Field(None, description="Local identifier for this record.")
    identifierType: Optional[str] = Field(None, description="Type of identifier (e.g., LegalEntityIdentifier).")
    scheme: Optional[str] = Field(None, description="Identification scheme. Recommended values:  ISO_17442 (LEI), ISO_9362 (BIC), ISO_10383 (MIC),  US_SEC_CIK, US_FRB_RSSD, CH_UID, FATCA_GIIN, DNB_DUNS. ")
    value: Optional[str] = Field(None, description="The actual identifier value.")
    issuingAuthority: Optional[str] = Field(None, description="Organization that issued the identifier.")
    status: Optional[str] = Field(None, description="Status of the identifier (e.g., active).")
    globallyUnique: Optional[bool] = Field(None, description="Whether the identifier is globally unique.")

class LegalIdentity(BaseModel):
    """
    Legal identification details of the entity.
    """
    legalName: Optional[str] = Field(None, description="Official registered name.")
    legalForm: Optional[str] = Field(None, description="e.g., corporation, cooperative, foundation, SPV.")
    domicileCountry: Optional[Country] = Field(None, description="Country of domicile.")
    registeredAddressCountry: Optional[Country] = Field(None, description="Country of the registered address.")
    headquartersCountry: Optional[Country] = Field(None, description="Country where the headquarters are located.")

class CorporateHierarchy(BaseModel):
    """
    Information about the parent entities.
    """
    directParent: Optional[ParentLink] = Field(None, description="Information about the direct parent.")
    ultimateParent: Optional[ParentLink] = Field(None, description="Information about the ultimate parent.")

class ParentLink(BaseModel):
    """
    Link to a parent entity.
    """
    lei: Optional[str] = Field(None, description="LEI of the parent entity.")

class IssuerMetadata(BaseModel):
    """
    Metadata regarding the issuer information.
    """
    sourceOfTruth: Optional[str] = Field(None, description="The source from which the data was obtained.")
    publicReference: Optional[bool] = Field(None, description="Whether this is a public reference.")
    renewalRequired: Optional[bool] = Field(None, description="Whether the data requires periodic renewal.")

class Guarantor(Issuer):
    """
    Entity offering a guarantee for certain instruments.
    """
    pass

class GicsClassification(BaseModel):
    """
    Classification of an issuer or instrument according to the GICS hierarchy.

    """
    sectorCode: Optional[str] = Field(None, description="2-digit code representing the GICS Sector.")
    industryGroupCode: Optional[str] = Field(None, description="4-digit code representing the GICS Industry Group.")
    industryCode: Optional[str] = Field(None, description="6-digit code representing the GICS Industry.")
    subIndustryCode: Optional[str] = Field(None, description="8-digit code representing the GICS Sub-Industry.")

class GicsReferenceData(BaseModel):
    """
    Structure for GICS reference data including the hierarchy.
    """
    standard: Optional[GicsStandardInfo] = None
    hierarchy: Optional[List[GicsSector]] = None

class GicsStandardInfo(BaseModel):
    """
    General information about the GICS standard.
    """
    name: Optional[str] = None
    abbreviation: Optional[str] = None
    owners: Optional[List[str]] = None
    standardType: Optional[str] = None
    isoStandard: Optional[bool] = None

class GicsSector(BaseModel):
    """
    GICS Sector (Level 1).
    """
    code: Optional[str] = None
    name: Optional[str] = None
    industryGroups: Optional[List[GicsIndustryGroup]] = None

class GicsIndustryGroup(BaseModel):
    """
    GICS Industry Group (Level 2).
    """
    code: Optional[str] = None
    name: Optional[str] = None
    industries: Optional[List[GicsIndustry]] = None

class GicsIndustry(BaseModel):
    """
    GICS Industry (Level 3).
    """
    code: Optional[str] = None
    name: Optional[str] = None
    subIndustries: Optional[List[GicsSubIndustry]] = None

class GicsSubIndustry(BaseModel):
    """
    GICS Sub-Industry (Level 4).
    """
    code: Optional[str] = None
    name: Optional[str] = None

class TelekursClassification(BaseModel):
    """
    Classification of an issuer or instrument according to the Telekurs hierarchy.

    """
    sectorCode: Optional[str] = Field(None, description="Code representing the Telekurs Sector (Level 1).")
    industryGroupCode: Optional[str] = Field(None, description="Code representing the Telekurs Industry Group (Level 2).")
    industryCode: Optional[str] = Field(None, description="Code representing the Telekurs Industry (Level 3).")

class TelekursReferenceData(BaseModel):
    """
    Structure for Telekurs reference data including the hierarchy.
    """
    standard: Optional[TelekursStandardInfo] = None
    hierarchy: Optional[List[TelekursSector]] = None

class TelekursStandardInfo(BaseModel):
    """
    General information about the Telekurs standard.
    """
    name: Optional[str] = None
    abbreviation: Optional[str] = None
    owners: Optional[List[str]] = None
    standardType: Optional[str] = None
    isoStandard: Optional[bool] = None

class TelekursSector(BaseModel):
    """
    Telekurs Sector (Level 1).
    """
    code: Optional[str] = None
    name: Optional[str] = None
    industryGroups: Optional[List[TelekursIndustryGroup]] = None

class TelekursIndustryGroup(BaseModel):
    """
    Telekurs Industry Group (Level 2).
    """
    code: Optional[str] = None
    name: Optional[str] = None
    industries: Optional[List[TelekursIndustry]] = None

class TelekursIndustry(BaseModel):
    """
    Telekurs Industry (Level 3).
    """
    code: Optional[str] = None
    name: Optional[str] = None

class ClassificationSystem(BaseModel):
    """
    Defines a classification standard or taxonomy.

    """
    systemId: Optional[str] = Field(None, description="Unique identifier of the classification system")
    name: Optional[str] = Field(None, description="Human-readable name")
    provider: Optional[str] = Field(None, description="Owning organization or data vendor")
    classificationType: Optional[str] = None
    jurisdictionScope: Optional[str] = Field(None, description="Primary geographic or regulatory scope (e.g. CH, EU, Global)")
    proprietary: Optional[bool] = Field(None, description="Indicates whether the system is commercially licensed")
    version: Optional[str] = Field(None, description="Vendor or internal version identifier")

class ClassificationHierarchy(BaseModel):
    """
    Defines the ordered hierarchy levels for a classification system.

    """
    systemId: Optional[str] = None
    levels: Optional[Any] = None

class ClassificationNode(BaseModel):
    """
    Represents a single node in a classification hierarchy.

    """
    nodeId: Optional[str] = Field(None, description="Globally unique node identifier")
    systemId: Optional[str] = None
    level: Optional[int] = Field(None, description="Hierarchy depth (1 = top)")
    levelName: Optional[str] = Field(None, description="Name of the hierarchy level")
    code: Optional[str] = Field(None, description="Vendor or internal classification code")
    name: Optional[str] = Field(None, description="Display name of the classification")
    parentNodeId: Optional[str] = Field(None, description="Parent node reference (null for root nodes)")
    validFrom: Optional[Any] = Field(None, description="Node validity start date")
    validTo: Optional[Any] = Field(None, description="Node validity end date")

class ClassificationAssignment(BaseModel):
    """
    Assigns a classified entity to a terminal classification node.

    """
    assignmentId: Optional[str] = None
    systemId: Optional[str] = None
    appliesTo: Optional[Any] = None
    classificationNodeId: Optional[str] = Field(None, description="Must reference a terminal ClassificationNode")
    effectivePeriod: Optional[Any] = None
    additionalAttributes: Optional[Any] = None

class IcbClassification(BaseModel):
    """
    Classification of an issuer or instrument according to the ICB hierarchy.

    """
    industryCode: Optional[str] = Field(None, description="Code representing the ICB Industry (Level 1).")
    supersectorCode: Optional[str] = Field(None, description="Code representing the ICB Supersector (Level 2).")
    sectorCode: Optional[str] = Field(None, description="Code representing the ICB Sector (Level 3).")
    subsectorCode: Optional[str] = Field(None, description="Code representing the ICB Subsector (Level 4).")

class IcbReferenceData(BaseModel):
    """
    Structure for ICB reference data including the hierarchy.
    """
    standard: Optional[IcbStandardInfo] = None
    hierarchy: Optional[List[IcbIndustry]] = None

class IcbStandardInfo(BaseModel):
    """
    General information about the ICB standard.
    """
    name: Optional[str] = None
    abbreviation: Optional[str] = None
    owners: Optional[List[str]] = None
    standardType: Optional[str] = None
    isoStandard: Optional[bool] = None

class IcbIndustry(BaseModel):
    """
    ICB Industry (Level 1).
    """
    code: Optional[str] = None
    name: Optional[str] = None
    supersectors: Optional[List[IcbSupersector]] = None

class IcbSupersector(BaseModel):
    """
    ICB Supersector (Level 2).
    """
    code: Optional[str] = None
    name: Optional[str] = None
    sectors: Optional[List[IcbSector]] = None

class IcbSector(BaseModel):
    """
    ICB Sector (Level 3).
    """
    code: Optional[str] = None
    name: Optional[str] = None
    subsectors: Optional[List[IcbSubsector]] = None

class IcbSubsector(BaseModel):
    """
    ICB Subsector (Level 4).
    """
    code: Optional[str] = None
    name: Optional[str] = None

class CFIReferenceEntry(BaseModel):
    """
    Canonical reference-data entry for a CFI code.
    """
    code: str = Field(..., description="Full six-character CFI code.")
    category: str = Field(..., description="First character representing the high-level category.")
    group: str = Field(..., description="Second character representing the group.")
    cfiType: Optional[str] = Field(None, description="Third character representing the instrument type.")
    form: Optional[str] = Field(None, description="Fourth character representing legal or structural form.")
    underlying: Optional[str] = Field(None, description="Fifth character representing underlying or payoff characteristic.")
    additionalAttributes: Optional[str] = Field(None, description="Sixth character representing additional attributes.")
    label: Optional[str] = Field(None, description="Human-readable label for the code.")

class CFI(BaseModel):
    """
    Represents a Classification of Financial Instruments (CFI) code as defined by ISO 10962. A CFI code consists of six characters, each conveying specific structural information.

    """
    code: Optional[str] = Field(None, description="The full six-character CFI code. Example: ESVUFR (Equity, Share, Voting, Unrestricted, Free, Registered). ")
    category: Optional[str] = Field(None, description="The first character of the CFI code, representing the high-level instrument category. Examples: E (Equity), D (Debt), C (Entitlements/Funds), O (Options), F (Futures), S (Swaps). ")
    group: Optional[str] = Field(None, description="The second character of the CFI code, representing the instrument group within the category. ")
    cfiType: Optional[str] = Field(None, description="The third character of the CFI code, representing the specific instrument type. ")
    form: Optional[str] = Field(None, description="The fourth character of the CFI code, representing the form or structure of the instrument. ")
    underlying: Optional[str] = Field(None, description="The fifth character of the CFI code, representing the underlying or payoff characteristic. ")
    additionalAttributes: Optional[str] = Field(None, description="The sixth character of the CFI code, representing additional attributes. ")

class CfiStandardInfo(BaseModel):
    """
    Information about the ISO 10962 standard.
    """
    name: Optional[str] = Field(None, description="Classification of Financial Instruments (CFI).")
    isoStandard: Optional[str] = Field(None, description="ISO 10962.")
    authority: Optional[str] = Field(None, description="International Organization for Standardization (ISO).")

class CurrencyReferenceEntry(BaseModel):
    """
    Canonical reference-data entry for a currency.
    """
    code: str = Field(..., description="ISO 4217 alphabetic currency code.")
    numericCode: str = Field(..., description="ISO 4217 numeric currency code.")
    name: str = Field(..., description="Official currency name.")
    minorUnits: Optional[int] = Field(None, description="Number of decimal places used for the currency.")
    symbol: Optional[str] = Field(None, description="Common display symbol.")
    issuingCountry: Optional[Country] = Field(None, description="ISO 3166-1 alpha-2 country code of the issuing authority.")
    issuingAuthority: Optional[str] = Field(None, description="Monetary authority responsible for issuing the currency.")

class Country(RootModel):
    """
    ISO 3166-1 alpha-2 country code.
    """
    root: str

class CountryReferenceEntry(BaseModel):
    """
    Canonical reference-data entry for a country or territory.
    """
    code: Country = Field(..., description="ISO 3166-1 alpha-2 country code.")
    name: str = Field(..., description="English short name of the country or territory.")
    alpha3Code: Optional[str] = Field(None, description="ISO 3166-1 alpha-3 country code.")
    numericCode: Optional[str] = Field(None, description="ISO 3166-1 numeric country code.")

class BondGolden(BaseModel):
    """
    Golden (tier-3) record for a Bond instrument. One document per instrument, keyed by `goldenId`.

    """
    goldenId: str = Field(..., description="Stable internal primary key of the golden record.")
    cfiCode: Optional[CfiCode] = Field(None, description="ISO 10962 CFI code (classification, NOT an identifier). ")
    identifierList: Optional[List[FinancialInstrumentIdentification]] = Field(None, description="Per-instrument completeness — every identifier known for this bond (ISIN, FIGI, CUSIP, SEDOL, RIC, Bloomberg, …). ")
    longName: LongText = Field(..., description="Full bond name (issuer + coupon + maturity), used for free-text search.")
    shortName: Optional[ShortText] = Field(None, description="Short bond name for grids.")
    assetClass: str = Field(..., description="Resolved asset class label (e.g., \"Fixed Income / Government Bond\").")
    assetClassId: Optional[str] = Field(None, description="Reference to the canonical AssetClass record used for roll-ups.")
    bondSubType: Optional[str] = Field(None, description="Bond sub-type capturing the structural variant.")
    seniority: Optional[str] = Field(None, description="Bond seniority in the issuer's capital structure.")
    industrySector: Optional[IndustrySector] = Field(None, description="Canonical industry/sector classification of the issuer.")
    countryOfRisk: Optional[Country] = Field(None, description="ISO 3166-1 alpha-2 country of risk (typically issuer domicile).")
    currencyOfDenomination: Currency = Field(..., description="ISO 4217 currency in which the bond is denominated.")
    issueDate: Optional[date] = Field(None, description="Issue date of the bond.")
    maturityDate: date = Field(..., description="Maturity date of the bond.")
    maturityBucket: Optional[str] = Field(None, description="Derived maturity bucket used by screens.")
    interestRate: Optional[InterestRate] = Field(None, description="Interest-rate definition (fixed / floating / staggered, day-count, payment cadence).")
    couponType: Optional[str] = Field(None, description="Coupon type, hoisted from interestRate.type for fast filters.")
    currentCouponRate: Optional[float] = Field(None, description="Currently effective coupon rate (decimal, hoisted for screens).")
    minimumDenomination: Optional[float] = Field(None, description="Minimum denomination allowed for trading.")
    minimumIncrement: Optional[float] = Field(None, description="Minimum tradable increment.")
    isCallable: Optional[bool] = Field(None, description="True if the bond carries an issuer call option.")
    isPuttable: Optional[bool] = Field(None, description="True if the bond carries a holder put option.")
    isConvertible: Optional[bool] = Field(None, description="True if the bond converts to equity under defined terms.")
    conversionPrice: Optional[Price] = Field(None, description="Conversion price for convertible bonds.")
    underlyingIsin: Optional[str] = Field(None, description="ISIN of the underlying instrument for structured / convertible bonds.")
    lifecycleStatus: Optional[str] = Field(None, description="Lifecycle status of the bond.")
    issuer: IssuerSnapshot = Field(..., description="Flattened issuer snapshot — legal name, LEI, domicile, credit, ESG.")
    primaryListing: Optional[ListingSnapshot] = Field(None, description="Primary trading venue listing for the bond.")
    secondaryListings: Optional[List[ListingSnapshot]] = Field(None, description="All other venues where the bond is listed.")
    marketData: Optional[BondMarketDataSnapshotEmbedded] = Field(None, description="Last-known market data snapshot (typically EOD), including bond- specific yields and accrued interest. For intraday valuations the PMS should still query the pricing service. ")
    creditRisk: Optional[CreditRisk] = Field(None, description="Credit risk profile of the bond instrument (issue-level).")
    instrumentEsgProfile: Optional[ESGInstrumentProfile] = Field(None, description="ESG profile of the bond (instrument-specific overlay).")
    compliance: Optional[ComplianceFlags] = Field(None, description="Pre-resolved compliance flags used in screens and PMS rules.")
    recordMeta: GoldenRecordMeta = Field(..., description="Provenance and freshness metadata for the golden record.")

class IssuerSnapshot(BaseModel):
    """
    Flattened issuer view denormalized into the bond golden record.
    """
    issuerId: str = Field(..., description="Internal stable issuer id (matches Issuer.id in silver).")
    legalName: str = Field(..., description="Official registered name of the issuer.")
    lei: Optional[LegalEntityIdentifier] = Field(None, description="ISO 17442 Legal Entity Identifier.")
    issuerType: Optional[str] = Field(None, description="Issuer classification.")
    domicileCountry: Optional[Country] = Field(None, description="Country of domicile of the issuer.")
    headquartersCountry: Optional[Country] = Field(None, description="Country where the issuer's headquarters are located.")
    ultimateParentLei: Optional[str] = Field(None, description="LEI of the ultimate parent entity, if different.")
    guarantorLei: Optional[str] = Field(None, description="LEI of the guarantor, if the bond is guaranteed by a third party.")
    creditProfile: Optional[CreditProfile] = Field(None, description="Snapshot of the issuer's creditworthiness profile.")
    esgProfile: Optional[ESGProfile] = Field(None, description="Snapshot of the issuer's ESG profile.")

class ListingSnapshot(BaseModel):
    """
    Denormalized venue listing for the bond.
    """
    listingId: Optional[str] = Field(None, description="Internal listing identifier.")
    mic: str = Field(..., description="ISO 10383 Market Identifier Code of the venue.")
    venueName: Optional[str] = Field(None, description="Human-readable venue name.")
    venueCountry: Optional[Country] = Field(None, description="Country of the trading venue.")
    ticker: Optional[str] = Field(None, description="Venue-specific trading symbol, if any.")
    listingCurrency: Currency = Field(..., description="ISO 4217 currency of trades on this listing.")
    marketSegment: Optional[str] = Field(None, description="Venue market segment.")
    firstTradingDate: Optional[date] = Field(None, description="Date the bond first traded on this venue.")
    status: Optional[str] = Field(None, description="Status of the listing on this venue.")
    isPrimary: Optional[bool] = Field(None, description="True if this is the primary listing.")

class BondMarketDataSnapshotEmbedded(BaseModel):
    """
    Last-known market data values for a bond, including yields and accruals not present in the equity snapshot.

    """
    sourceListingId: Optional[str] = Field(None, description="Listing the snapshot was sourced from.")
    sourceMic: Optional[str] = Field(None, description="MIC of the source listing.")
    asOf: Optional[datetime] = Field(None, description="Timestamp of the snapshot.")
    cleanPrice: Optional[Price] = Field(None, description="Clean price (excluding accrued interest).")
    dirtyPrice: Optional[Price] = Field(None, description="Dirty price (including accrued interest).")
    accruedInterest: Optional[CurrencyAmount] = Field(None, description="Accrued interest at the snapshot.")
    yieldToMaturity: Optional[float] = Field(None, description="Yield to maturity (decimal).")
    yieldToWorst: Optional[float] = Field(None, description="Yield to worst (decimal).")
    currentYield: Optional[float] = Field(None, description="Current yield (coupon / price, decimal).")
    modifiedDuration: Optional[float] = Field(None, description="Modified duration in years.")
    macaulayDuration: Optional[float] = Field(None, description="Macaulay duration in years.")
    convexity: Optional[float] = Field(None, description="Convexity of the bond.")
    spreadToBenchmark: Optional[float] = Field(None, description="Spread (bp) to the relevant benchmark curve.")
    zSpread: Optional[float] = Field(None, description="Z-spread (bp).")
    oasSpread: Optional[float] = Field(None, description="Option-adjusted spread (bp).")

class ComplianceFlags(BaseModel):
    """
    Pre-resolved regulatory / compliance flags for the bond.
    """
    isUcitsEligible: Optional[bool] = Field(None, description="True if eligible for UCITS portfolios.")
    isPrIIPs: Optional[bool] = Field(None, description="True if a PRIIPs KID applies.")
    isSanctionsListed: Optional[bool] = Field(None, description="True if the issuer or instrument appears on a tracked sanctions list.")
    sanctionsLists: Optional[List[str]] = Field(None, description="Sanctions lists where the instrument or issuer is currently listed.")
    isHighYield: Optional[bool] = Field(None, description="True if classified as high-yield (sub-investment-grade).")
    isGreenBond: Optional[bool] = Field(None, description="True if labelled as a green bond per ICMA principles.")
    isSocialBond: Optional[bool] = Field(None, description="True if labelled as a social bond per ICMA principles.")
    isSustainabilityLinked: Optional[bool] = Field(None, description="True if structured as a sustainability-linked bond.")
    mifid2TargetMarket: Optional[str] = Field(None, description="MiFID II target-market category.")

class GoldenRecordMeta(BaseModel):
    """
    Provenance, freshness and lineage metadata for the golden record.
    """
    schemaVersion: str = Field(..., description="Version of the BondGolden schema this document conforms to.")
    goldenAsOf: datetime = Field(..., description="Timestamp at which this golden record was assembled.")
    ingestionRunId: Optional[str] = Field(None, description="Run id of the enrichment pipeline that produced this record.")
    sourceOfTruth: List[SourceAttribution] = Field(..., description="Map of field-group to source system.")
    sourceFingerprints: Optional[List[SourceFingerprint]] = Field(None, description="Content hashes of contributing silver documents.")
    qualityScore: Optional[float] = Field(None, description="Aggregate data-quality score (0.0 - 1.0).")
    isActive: Optional[bool] = Field(None, description="True if this is the currently active golden record for the instrument.")

class SourceAttribution(BaseModel):
    """
    Records which upstream system contributed a particular field group.
    """
    fieldGroup: str = Field(..., description="Field group inside the golden record.")
    source: str = Field(..., description="Upstream system or vendor.")
    sourceTimestamp: Optional[datetime] = Field(None, description="Timestamp at the source when the data was produced.")

class SourceFingerprint(BaseModel):
    """
    Content hash of an upstream silver document.
    """
    sourceEntity: str = Field(..., description="Silver entity reference (e.g., \"Bond:DE0001102309\").")
    fingerprint: str = Field(..., description="Stable hash (e.g., SHA-256) at assembly time.")

class PositionGolden(BaseModel):
    """
    Golden (tier-3) record for a single position. One document per position-date / account / instrument tuple, keyed by `goldenId`.
The grain is intentionally `(accountId, instrumentId, positionDate)` so the index supports both "current positions" queries (filter by latest `positionDate`) and "as-of" queries (filter by a historical date).

    """
    goldenId: str = Field(..., description="Stable internal primary key of the position golden record.")
    positionId: str = Field(..., description="Position id assigned by the source system (matches silver Position.id).")
    portfolioId: str = Field(..., description="Identifier of the containing portfolio.")
    portfolioName: Optional[str] = Field(None, description="Human-readable portfolio name.")
    accountId: str = Field(..., description="Identifier of the holding account.")
    accountName: Optional[str] = Field(None, description="Display name of the account.")
    accountType: Optional[str] = Field(None, description="Type of account (custody, cash, lombard, segregated, etc.).")
    custodianId: Optional[str] = Field(None, description="Identifier of the custodian holding the position.")
    custodianBic: Optional[str] = Field(None, description="BIC of the custodian / safekeeping place.")
    customerId: Optional[str] = Field(None, description="Identifier of the end customer holding the portfolio.")
    relationshipManagerId: Optional[str] = Field(None, description="Identifier of the relationship manager (advisor).")
    instrumentRef: InstrumentRef = Field(..., description="Compact reference to the instrument golden record, with the handful of fields a PMS row needs without re-fetching the full instrument document. ")
    positionDate: date = Field(..., description="Valuation / as-of date of this position record.")
    endOfDayIndicator: Optional[bool] = Field(None, description="True if this snapshot represents an end-of-day position.")
    tradeDate: Optional[date] = Field(None, description="Trade date of the originating transaction (when first opened).")
    settlementDate: Optional[date] = Field(None, description="Settlement date of the originating transaction.")
    quantity: Quantity = Field(..., description="Total quantity held in the position.")
    blockedQuantity: Optional[Quantity] = Field(None, description="Quantity that is blocked (collateral, pledge, pending).")
    settledQuantity: Optional[Quantity] = Field(None, description="Quantity that has fully settled.")
    pendingQuantity: Optional[Quantity] = Field(None, description="Quantity from trades not yet settled.")
    valuation: ValuationSnapshot = Field(..., description="Market valuation snapshot for the position.")
    costBasis: Optional[CostBasisSnapshot] = Field(None, description="Cost basis snapshot used by P&L and tax reporting.")
    accruals: Optional[AccrualsSnapshot] = Field(None, description="Income accruals (interest, pending dividends).")
    portfolioCurrency: Optional[Currency] = Field(None, description="Reference currency of the parent portfolio.")
    positionCurrency: Optional[Currency] = Field(None, description="Currency in which the position is denominated.")
    fxRateToPortfolio: Optional[float] = Field(None, description="FX rate used to convert position currency into portfolio currency.")
    portfolioWeight: Optional[float] = Field(None, description="Position weight in the portfolio (decimal, e.g. 0.045 for 4.5%).")
    lifecycleStatus: Optional[str] = Field(None, description="Status of the position.")
    isShortPosition: Optional[bool] = Field(None, description="True if the position is short (negative quantity).")
    isHedge: Optional[bool] = Field(None, description="True if the position is tagged as a hedge.")
    recordMeta: GoldenRecordMeta = Field(..., description="Provenance and freshness metadata for the position golden record.")

class InstrumentRef(BaseModel):
    """
    Compact instrument reference embedded in the position. Carries the ids needed to look up the full instrument golden record plus enough descriptive fields to render the position row without an extra fetch.

    """
    instrumentGoldenId: str = Field(..., description="Foreign key to the instrument golden record (Equity/Bond/Fund/...).")
    instrumentType: str = Field(..., description="Discriminator pointing to the instrument golden family.")
    isin: Optional[str] = Field(None, description="ISO 6166 ISIN of the instrument.")
    figi: Optional[str] = Field(None, description="OpenFIGI identifier of the instrument.")
    tickerSymbol: Optional[str] = Field(None, description="Primary ticker symbol.")
    exchangeMic: Optional[str] = Field(None, description="MIC of the primary listing.")
    cfiCode: Optional[CfiCode] = Field(None, description="CFI code of the instrument.")
    longName: Optional[LongText] = Field(None, description="Full instrument name.")
    shortName: Optional[ShortText] = Field(None, description="Short instrument name.")
    assetClass: Optional[str] = Field(None, description="Asset class label (mirrors instrument golden record).")
    assetClassId: Optional[str] = Field(None, description="Asset class id (for roll-ups).")
    industrySector: Optional[IndustrySector] = Field(None, description="Industry / sector classification of the instrument or issuer.")
    countryOfRisk: Optional[Country] = Field(None, description="Country of risk of the instrument.")
    instrumentCurrency: Optional[Currency] = Field(None, description="Currency in which the instrument is denominated.")
    issuerLei: Optional[LegalEntityIdentifier] = Field(None, description="LEI of the issuer.")
    issuerName: Optional[str] = Field(None, description="Legal name of the issuer.")

class ValuationSnapshot(BaseModel):
    """
    Market valuation of the position at `positionDate`.
    """
    valuationDate: date = Field(..., description="Date of the valuation.")
    marketPrice: Optional[Price] = Field(None, description="Market price used for valuation.")
    priceType: Optional[str] = Field(None, description="Indicates which type of price is used.")
    valueInPositionCurrency: Optional[CurrencyAmount] = Field(None, description="Market value of the position in its denomination currency.")
    valueInReferenceCurrency: Optional[CurrencyAmount] = Field(None, description="Market value of the position in the portfolio reference currency.")

class CostBasisSnapshot(BaseModel):
    """
    Cost basis information for the position.
    """
    averageCostPrice: Optional[Price] = Field(None, description="Weighted-average acquisition cost per unit.")
    totalAcquisitionCost: Optional[CurrencyAmount] = Field(None, description="Total acquisition cost in position currency.")
    costForeignExchangeRate: Optional[float] = Field(None, description="FX rate used for cost conversion.")
    unrealizedPL: Optional[CurrencyAmount] = Field(None, description="Unrealized P&L in position currency.")
    unrealizedPLInReferenceCurrency: Optional[CurrencyAmount] = Field(None, description="Unrealized P&L in portfolio reference currency.")
    unrealizedPLPercentage: Optional[float] = Field(None, description="Unrealized P&L as a decimal of cost (e.g., 0.24 for 24%).")
    bookValue: Optional[CurrencyAmount] = Field(None, description="Accounting book value of the position.")

class AccrualsSnapshot(BaseModel):
    """
    Income accruals attached to the position.
    """
    accruedInterest: Optional[CurrencyAmount] = Field(None, description="Accrued interest at the snapshot (bond-like instruments).")
    numberOfDaysAccrued: Optional[int] = Field(None, description="Number of days of accrued interest.")
    pendingDividends: Optional[CurrencyAmount] = Field(None, description="Declared but not yet paid dividend amount.")

class InstrumentSearch(BaseModel):
    """
    One search-friendly projection of a per-security golden record. Document `_id` is `<scope>:<documentId>` (e.g. `fund:FG-IE00B4L5Y983-001`).

    """
    documentId: str = Field(..., description="goldenId of the source per-security record.")
    scope: str = Field(..., description="Which per-security index holds the canonical record.")
    ow_type: Optional[str] = Field(None, description="OpenWealth FinancialInstrumentType (`equity`, `simpleBond`, `fund`) — what the frontend type tabs filter on. ")
    longName: str = Field(..., description="Full instrument name.")
    shortName: Optional[str] = Field(None, description="Short display name.")
    assetClass: str = Field(..., description="Resolved asset-class label.")
    assetClassId: Optional[str] = Field(None, description="Canonical asset-class id.")
    cfiCode: Optional[str] = Field(None, description="ISO 10962 CFI code.")
    currency: Optional[str] = Field(None, description="ISO 4217 currency code.")
    country: Optional[str] = Field(None, description="ISO 3166-1 alpha-2 country (incorporation / domicile / risk).")
    venueMic: Optional[str] = Field(None, description="Primary listing MIC.")
    ticker: Optional[str] = Field(None, description="Primary listing ticker.")
    issuerLegalName: Optional[str] = Field(None, description="Display issuer name. For equities and bonds this is the instrument's issuer. For funds it's the umbrella (legal issuer of the share class). ")
    issuerLei: Optional[str] = Field(None, description="LEI of the display issuer if known.")
    managementCompanyName: Optional[str] = Field(None, description="Fund only — operator legal name.")
    promoterName: Optional[str] = Field(None, description="Fund only — group / promoter name.")
    valor: Optional[str] = Field(None, description="Swiss VALOREN identifier (when present).")
    sector: Optional[str] = Field(None, description="Equity — sector / industry label (yahoo or canonical).")
    couponRate: Optional[float] = Field(None, description="Bond — current coupon rate as a decimal fraction (0.015 = 1.5%).")
    maturityDate: Optional[date] = Field(None, description="Bond — maturity date.")
    issuerRating: Optional[str] = Field(None, description="Bond — issuer's primary credit-rating notation (e.g. \"BBB-\"). Taken from the first entry of `issuer.creditProfile.issuerRatings`. ")
    subFundName: Optional[str] = Field(None, description="Fund — sub-fund name (strategy level).")
    umbrellaName: Optional[str] = Field(None, description="Fund — umbrella legal name (issuer of the share class).")
    fundSubType: Optional[str] = Field(None, description="Fund — sub-type (etf, open_ended_mutual_fund, …).")
    dividendPolicy: Optional[str] = Field(None, description="Fund — DISTRIBUTING / ACCUMULATING.")
    totalExpenseRatio: Optional[float] = Field(None, description="Fund — TER as a decimal fraction (0.002 = 0.20 %).")
    primaryAssetClassExposure: Optional[str] = Field(None, description="Fund — dominant underlying exposure (equity / fixedIncome / mixed_balanced / …).")
    identifiers: Optional[List[Dict[str, Any]]] = Field(None, description="All known identifiers with scheme labels.")
    identifierStrings: Optional[List[str]] = Field(None, description="Flat list of every identifier value across all schemes — indexed both as `text` (substring search) and `keyword` (exact match). The fastest path for \"user typed AAPL\". ")
    lifecycleStatus: Optional[str] = Field(None, description="active / matured / liquidated / inactive / ...")
    qualityScore: Optional[float] = Field(None, description="Provenance quality score copied from recordMeta.")
    goldenAsOf: Optional[datetime] = Field(None, description="When the source record was last rebuilt.")

class Identifier(BaseModel):
    """
    One (security, identifier) entry. The combination of `(scheme, identifier, documentId)` is the natural unique key (also used as the OpenSearch `_id`).

    """
    identifier: str = Field(..., description="The identifier value as users would search for it (no normalisation beyond the source format). ")
    scheme: str = Field(..., description="Identifier scheme. This enum is intentionally limited to *identifiers*. Classification codes (CFI / ISO 10962, GICS, ICB, NACE) are NOT identifiers and do not appear here. ")
    scope: str = Field(..., description="Which per-security golden index holds the canonical record. Maps directly to the OpenSearch index name as `pms_golden_<scope>`. ")
    documentId: str = Field(..., description="`goldenId` of the per-security golden record this identifier belongs to. ")

class EquityGolden(BaseModel):
    """
    Golden (tier-3) record for an Equity instrument. One document per instrument, keyed by `goldenId`. Designed to be the primary OpenSearch document a PMS reads to render instrument detail, run screens, and attribute positions without joining secondary stores.

    """
    goldenId: str = Field(..., description="Stable, internal primary key of the golden record. Independent of external identifiers so the record survives corporate-action re-identification (re-ISIN, ticker change). ")
    cfiCode: Optional[CfiCode] = Field(None, description="ISO 10962 CFI code (classification, NOT an identifier). ")
    identifierList: Optional[List[FinancialInstrumentIdentification]] = Field(None, description="Per-instrument completeness — every identifier known for this security (ISIN, FIGI, SEDOL, CUSIP, RIC, WKN, VALOREN, Bloomberg, …). ")
    longName: LongText = Field(..., description="Full instrument name, used for free-text search and display.")
    shortName: Optional[ShortText] = Field(None, description="Short instrument name, for grids and compact UIs.")
    assetClass: str = Field(..., description="Resolved asset class label (e.g., \"Equity / Common Stock\"). Derived from AssetClass mapping rules against the CFI code and instrument type. ")
    assetClassId: Optional[str] = Field(None, description="Reference to the canonical AssetClass record used for roll-ups.")
    equitySubType: Optional[str] = Field(None, description="Equity sub-type (Common, Preferred, ADR, GDR, REIT, etc.).")
    shareClass: Optional[str] = Field(None, description="Share class (e.g., Class A, Class B, Preferred).")
    industrySector: Optional[IndustrySector] = Field(None, description="Canonical industry/sector classification snapshot. Includes the assigned taxonomy code (GICS/ICB/Telekurs) and the canonical label used by the PMS for cross-source comparability. ")
    incorporationCountry: Optional[Country] = Field(None, description="ISO 3166-1 alpha-2 country of incorporation of the issuing company.")
    currencyOfDenomination: Currency = Field(..., description="ISO 4217 currency in which the equity is denominated.")
    parValue: Optional[CurrencyAmount] = Field(None, description="Nominal par value stated in the corporate charter.")
    votingRatio: Optional[float] = Field(None, description="Number of votes per share.")
    hasVotingRights: Optional[bool] = Field(None, description="True if the equity carries voting rights.")
    sharesOutstanding: Optional[float] = Field(None, description="Total shares currently issued and outstanding.")
    issuer: IssuerSnapshot = Field(..., description="Flattened snapshot of issuer attributes a PMS needs at the equity row level — legal name, LEI, domicile, ratings — without joining to the issuer store. ")
    primaryListing: ListingSnapshot = Field(..., description="Primary trading venue listing for the equity.")
    secondaryListings: Optional[List[ListingSnapshot]] = Field(None, description="All other venues where the equity is listed.")
    marketData: Optional[MarketDataSnapshotEmbedded] = Field(None, description="Last-known market data snapshot (typically EOD). For intraday valuations the PMS should still query the pricing service; this snapshot is the OpenSearch-resident fallback and search input. ")
    dividendStatus: Optional[bool] = Field(None, description="True if the equity currently pays dividends.")
    dividendPolicy: Optional[DividendPolicy] = Field(None, description="Dividend policy snapshot (yield, frequency, last payment date).")
    keyFigures: Optional[KeyFigures] = Field(None, description="Key valuation figures (market cap, EPS, P/E, volatility).")
    compliance: Optional[ComplianceFlags] = Field(None, description="Pre-resolved compliance flags used in screens and PMS rules.")
    lifecycleStatus: Optional[str] = Field(None, description="Lifecycle status of the equity (active / suspended / delisted / merged).")
    firstTradingDate: Optional[date] = Field(None, description="Date the equity was first admitted to trading.")
    delistingDate: Optional[date] = Field(None, description="Date of delisting, if applicable.")
    recordMeta: GoldenRecordMeta = Field(..., description="Provenance and freshness metadata for the golden record.")

class MarketDataSnapshotEmbedded(BaseModel):
    """
    Last-known market data values for the equity, denormalized for inclusion in the golden record. References the source listing by MIC + listingId.

    """
    sourceListingId: Optional[str] = Field(None, description="Listing the snapshot was sourced from.")
    sourceMic: Optional[str] = Field(None, description="MIC of the listing the snapshot was sourced from.")
    asOf: Optional[datetime] = Field(None, description="Timestamp of the snapshot.")
    lastTradePrice: Optional[Price] = Field(None, description="Most recent traded price.")
    open: Optional[float] = Field(None, description="Opening price of the trading session.")
    high: Optional[float] = Field(None, description="Intraday or session high price.")
    low: Optional[float] = Field(None, description="Intraday or session low price.")
    close: Optional[float] = Field(None, description="Closing price of the trading session.")
    volume: Optional[float] = Field(None, description="Traded volume for the period of the snapshot.")
    vwap: Optional[float] = Field(None, description="Volume-weighted average price for the period.")
    marketCapCategory: Optional[str] = Field(None, description="Market-cap bucket (Large-Cap, Mid-Cap, Small-Cap, etc.).")

class IssuerGolden(BaseModel):
    """
    Canonical legal-entity record for an instrument issuer. Document `_id` is `issuerId`.

    """
    goldenId: str = Field(..., description="Stable synthetic identifier for the issuer record.")
    issuerId: str = Field(..., description="Stable internal issuer identifier. Equals `IssuerSnapshot.issuerId` on all instruments that reference this issuer. When the LEI is present, the convention is `ISS-<LEI>`; otherwise a slug of `legalName`. ")
    lei: Optional[LegalEntityIdentifier] = Field(None, description="ISO 17442 Legal Entity Identifier.")
    legalName: str = Field(..., description="Official legal name of the issuer.")
    issuerType: Optional[str] = Field(None, description="Coarse-grained issuer type. Examples: corporate, government, supranational, bank, insurance_company, fund_company, special_purpose. ")
    domicileCountry: Optional[Country] = Field(None, description="ISO 3166-1 alpha-2 country of legal domicile.")
    headquartersCountry: Optional[Country] = Field(None, description="ISO 3166-1 alpha-2 country of operational headquarters.")
    ultimateParentLei: Optional[str] = Field(None, description="LEI of the ultimate parent (group head) if applicable.")
    guarantorLei: Optional[str] = Field(None, description="LEI of an explicit external guarantor, if any.")
    creditProfile: Optional[CreditProfile] = Field(None, description="Aggregated credit ratings across agencies.")
    esgProfile: Optional[ESGProfile] = Field(None, description="Aggregated ESG ratings and labels.")
    instrumentsByClass: Optional[Dict[str, Any]] = Field(None, description="Count of per-instrument golden documents that reference this issuer, broken down by `pms_golden_<scope>` family. Maintained by the aggregator. ")
    instrumentCount: Optional[int] = Field(None, description="Total number of instruments referencing this issuer.")
    recordMeta: GoldenRecordMeta

class FundGolden(BaseModel):
    """
    Golden (tier-3) record for a Fund instrument. One document per share class / sub-fund, keyed by `goldenId`.

    """
    goldenId: str = Field(..., description="Stable internal primary key of the golden record. By convention embeds the ISIN substring for legibility but is otherwise opaque. ")
    cfiCode: Optional[CfiCode] = Field(None, description="ISO 10962 CFI code (classification, NOT an identifier). Stays at top level because the fund itself is classified; same code for every share class of the same sub-fund. ")
    identifierList: Optional[List[FinancialInstrumentIdentification]] = Field(None, description="Per-instrument completeness — every identifier known for this security (ISIN, FIGI, SEDOL, CUSIP, RIC, WKN, VALOREN, Bloomberg ticker, …). Different purpose from the helper index: that's for cross-security lookup, this is for \"show me everything I know about THIS one\". ")
    longName: LongText = Field(..., description="Full fund name including share class.")
    shortName: Optional[ShortText] = Field(None, description="Short fund name for grids.")
    umbrella: UmbrellaSnapshot = Field(..., description="Full umbrella entity snapshot (LEI, domicile, structure).")
    subFund: Optional[SubFund] = Field(None, description="Sub-fund-level grouping inside the umbrella.")
    shareClass: Optional[ShareClass] = Field(None, description="Share-class-level grouping. ISIN, currency and the hedging flag live here — they discriminate share classes inside the sub-fund. For cross-security identifier lookups, use the helper index (`pms_golden_identifier`). ")
    assetClass: str = Field(..., description="Resolved asset class label (e.g., \"Fund / Equity ETF\").")
    assetClassId: Optional[str] = Field(None, description="Reference to the canonical AssetClass record used for roll-ups.")
    fundSubType: Optional[str] = Field(None, description="Fund sub-type / wrapper.")
    fundStrategy: Optional[str] = Field(None, description="Investment strategy classification.")
    primaryAssetClassExposure: Optional[str] = Field(None, description="Dominant underlying asset class exposure.")
    currencyOfDenomination: Currency = Field(..., description="ISO 4217 currency of the share class.")
    domicile: Optional[str] = Field(None, description="Country where the fund is legally registered and regulated.")
    legalFramework: Optional[str] = Field(None, description="Regulatory framework (UCITS, AIFMD, 40-Act, etc.).")
    legalStructure: Optional[str] = Field(None, description="Legal form (SICAV, ICAV, FCP, LP, etc.).")
    dividendPolicy: Optional[str] = Field(None, description="Income handling (distributing vs accumulating).")
    isCurrencyHedged: Optional[bool] = Field(None, description="True if the share class employs FX hedging.")
    hedgingCurrency: Optional[Currency] = Field(None, description="Target currency into which exposures are hedged.")
    holdingsCount: Optional[int] = Field(None, description="Total number of underlying holdings in the fund.")
    replicationMethod: Optional[str] = Field(None, description="How the fund replicates its strategy (ETF specific, optional).")
    benchmarkName: Optional[str] = Field(None, description="Name of the tracked benchmark (e.g., MSCI World Net TR).")
    benchmarkIdentifier: Optional[str] = Field(None, description="Identifier of the tracked benchmark, if known.")
    fiscalYearEnd: Optional[str] = Field(None, description="Fund fiscal year end as MM-DD.")
    rebalanceFrequency: Optional[str] = Field(None, description="Portfolio rebalance frequency (mainly for index-tracking funds).")
    riskRating: Optional[RiskRating] = Field(None, description="Regulatory KIID / PRIIPs KID risk ratings.")
    totalExpenseRatio: Optional[float] = Field(None, description="TER (annual %, decimal) hoisted from fees.ongoing for screens.")
    transactionCostsPRIIPs: Optional[float] = Field(None, description="PRIIPs ex-post transaction-cost ratio (decimal, annualised).")
    swingPricingApplied: Optional[bool] = Field(None, description="True if swing pricing is applied to NAV calculation.")
    fees: Optional[FundFeeStructure] = Field(None, description="Full fee structure snapshot.")
    dealing: Optional[DealingTerms] = Field(None, description="Subscription / redemption mechanics for the share class.")
    serviceProviders: Optional[ServiceProviders] = Field(None, description="Depositary, administrator, transfer agent, auditor, promoter.")
    assetAllocation: Optional[AssetAllocation] = Field(None, description="Allocation buckets and look-through top holdings.")
    holdingsAsOf: Optional[date] = Field(None, description="As-of date of the holdings / allocation snapshot.")
    lookthroughProvenance: Optional[LookthroughProvenance] = Field(None, description="Provenance metadata when `assetAllocation.holdings` is proxy-derived. Null when all holdings carry `source: direct` (the standard case). ")
    portfolioTurnoverPctAnnual: Optional[float] = Field(None, description="Annualised portfolio turnover ratio (decimal).")
    currencyAllocation: Optional[List[Dict[str, Any]]] = Field(None, description="Allocation of fund holdings by underlying currency.")
    performance: Optional[PerformanceSnapshot] = Field(None, description="Standard performance and risk-adjusted metrics for the share class.")
    taxStatuses: Optional[TaxStatuses] = Field(None, description="Jurisdiction-specific tax status overlays.")
    managementCompany: OrganisationSnapshot = Field(..., description="Management company / operator snapshot.")
    investmentManager: Optional[OrganisationSnapshot] = Field(None, description="Delegated portfolio manager, if different from the management company (UCITS ManCos commonly delegate to a separately licensed advisor, e.g. BlackRock Advisors UK Ltd). ")
    promoter: Optional[OrganisationSnapshot] = Field(None, description="Group / parent that promotes (sponsors) the fund. Corporate hierarchy, not a service-administration role. ")
    primaryListing: Optional[ListingSnapshot] = Field(None, description="Primary venue listing for the ETF.")
    secondaryListings: Optional[List[ListingSnapshot]] = Field(None, description="Cross-listings for the ETF.")
    marketData: Optional[FundMarketDataSnapshotEmbedded] = Field(None, description="Latest NAV / market price snapshot.")
    instrumentEsgProfile: Optional[ESGInstrumentProfile] = Field(None, description="ESG profile of the fund.")
    inceptionDate: Optional[date] = Field(None, description="Inception date of the share class.")
    terminationDate: Optional[date] = Field(None, description="Termination date, if applicable.")
    lifecycleStatus: Optional[str] = Field(None, description="Lifecycle status of the fund.")
    compliance: Optional[ComplianceFlags] = Field(None, description="Pre-resolved compliance flags used in PMS screens.")
    recordMeta: GoldenRecordMeta = Field(..., description="Provenance and freshness metadata for the golden record.")

class OrganisationSnapshot(BaseModel):
    """
    Polymorphic organisation snapshot — used for `managementCompany`, `investmentManager` and `promoter`. `organisationType` discriminates.

    """
    organisationId: str = Field(..., description="Internal stable organisation id.")
    legalName: str = Field(..., description="Official registered name of the organisation.")
    lei: Optional[LegalEntityIdentifier] = Field(None, description="ISO 17442 Legal Entity Identifier.")
    organisationType: Optional[str] = Field(None, description="Organisation classification.")
    domicileCountry: Optional[Country] = Field(None, description="Country of domicile of the organisation.")
    headquartersCountry: Optional[Country] = Field(None, description="Country where the organisation is headquartered.")
    ultimateParentLei: Optional[str] = Field(None, description="LEI of the ultimate parent group.")
    esgProfile: Optional[ESGProfile] = Field(None, description="ESG profile of the organisation.")

class FundMarketDataSnapshotEmbedded(BaseModel):
    """
    Latest NAV / price snapshot for the fund.
    """
    sourceListingId: Optional[str] = Field(None, description="Listing the snapshot was sourced from (ETF) or null.")
    sourceMic: Optional[str] = Field(None, description="MIC of the source listing.")
    asOf: Optional[datetime] = Field(None, description="Timestamp of the snapshot.")
    nav: Optional[Price] = Field(None, description="Net Asset Value per share.")
    navCurrency: Optional[Currency] = Field(None, description="Currency of the NAV.")
    navType: Optional[str] = Field(None, description="NAV calculation type.")
    sharesInIssue: Optional[float] = Field(None, description="Number of shares in issue at the NAV cut-off.")
    indicativeNav: Optional[Price] = Field(None, description="Intraday indicative NAV (iNAV) for ETFs.")
    marketPrice: Optional[Price] = Field(None, description="Last traded market price (ETF), if different from NAV.")
    premiumDiscount: Optional[float] = Field(None, description="ETF market price premium / discount to NAV (decimal).")
    aum: Optional[CurrencyAmount] = Field(None, description="Assets under management of the fund (or share class).")
    open: Optional[float] = Field(None, description="Opening price of the trading session.")
    high: Optional[float] = Field(None, description="Intraday or session high price.")
    low: Optional[float] = Field(None, description="Intraday or session low price.")
    close: Optional[float] = Field(None, description="Closing price of the trading session.")
    volume: Optional[float] = Field(None, description="Traded volume for the period of the snapshot.")
    vwap: Optional[float] = Field(None, description="Volume-weighted average price for the period.")
    ytdReturn: Optional[float] = Field(None, description="Year-to-date total return (decimal).")
    oneYearReturn: Optional[float] = Field(None, description="Trailing one-year total return (decimal).")
    threeYearReturn: Optional[float] = Field(None, description="Trailing three-year annualised return (decimal).")
    fiveYearReturn: Optional[float] = Field(None, description="Trailing five-year annualised return (decimal).")
    volatility1y: Optional[float] = Field(None, description="Trailing one-year realised volatility (decimal).")

class UmbrellaSnapshot(BaseModel):
    """
    Snapshot of the umbrella entity that hosts the sub-fund.
    """
    umbrellaId: Optional[str] = Field(None, description="Internal stable umbrella id.")
    legalName: str = Field(..., description="Legal name of the umbrella entity.")
    lei: Optional[LegalEntityIdentifier] = Field(None, description="ISO 17442 LEI of the umbrella entity.")
    domicileCountry: Optional[Country] = Field(None, description="Country of domicile of the umbrella.")
    legalStructure: Optional[str] = Field(None, description="Legal form of the umbrella (plc, SICAV, FCP, ICAV, ...).")

class RiskRating(BaseModel):
    """
    Regulatory KIID / PRIIPs KID risk ratings.
    """
    srri: Optional[int] = Field(None, description="UCITS KIID Synthetic Risk and Reward Indicator (1-7, legacy).")
    sri: Optional[int] = Field(None, description="PRIIPs KID Summary Risk Indicator (1-7).")

class DealingTerms(BaseModel):
    """
    Subscription / redemption mechanics for the share class.
    """
    dealingFrequency: Optional[str] = Field(None, description="How often the fund accepts subscriptions / redemptions.")
    settlementCycle: Optional[str] = Field(None, description="Trade-to-settlement cycle (e.g., T+2).")
    cutoffTimeLocal: Optional[str] = Field(None, description="Daily dealing cut-off time in the fund's local timezone (HH:MM).")
    cutoffTimezone: Optional[str] = Field(None, description="IANA timezone of the dealing cut-off.")
    minimumInitialInvestment: Optional[float] = Field(None, description="Minimum initial investment in the share class currency.")
    minimumSubsequentInvestment: Optional[float] = Field(None, description="Minimum subsequent investment in the share class currency.")

class PartyReference(BaseModel):
    """
    Lightweight reference to a service provider / counterparty.
    """
    legalName: str = Field(..., description="Registered legal name of the party.")
    lei: Optional[LegalEntityIdentifier] = Field(None, description="ISO 17442 LEI of the party, if known.")

class ServiceProviders(BaseModel):
    """
    Standard fund service-provider snapshot.
    """
    depositary: Optional[PartyReference] = Field(None, description="Depositary / custodian for the fund's assets.")
    administrator: Optional[PartyReference] = Field(None, description="Fund administrator (NAV calculation, books and records).")
    transferAgent: Optional[PartyReference] = Field(None, description="Transfer agent (shareholder register and dealing).")
    auditor: Optional[PartyReference] = Field(None, description="External auditor of the fund's accounts.")

class ReturnsBreakdown(BaseModel):
    """
    Total return measurements for standard horizons.
    """
    oneMonth: Optional[float] = Field(None, description="Trailing 1-month total return (decimal).")
    threeMonth: Optional[float] = Field(None, description="Trailing 3-month total return (decimal).")
    ytd: Optional[float] = Field(None, description="Year-to-date total return (decimal).")
    oneYear: Optional[float] = Field(None, description="Trailing 1-year total return (decimal).")
    threeYearAnn: Optional[float] = Field(None, description="Trailing 3-year annualised total return (decimal).")
    fiveYearAnn: Optional[float] = Field(None, description="Trailing 5-year annualised total return (decimal).")
    tenYearAnn: Optional[float] = Field(None, description="Trailing 10-year annualised total return (decimal).")
    sinceInceptionAnn: Optional[float] = Field(None, description="Since-inception annualised total return (decimal).")

class PerformanceSnapshot(BaseModel):
    """
    Standard performance and risk-adjusted metrics for the share class.
    """
    asOf: Optional[date] = Field(None, description="As-of date of the performance snapshot.")
    returns: Optional[ReturnsBreakdown] = Field(None, description="Total returns for the share class.")
    benchmarkReturns: Optional[ReturnsBreakdown] = Field(None, description="Total returns for the tracked benchmark.")
    trackingError1y: Optional[float] = Field(None, description="Trailing 1-year tracking error to benchmark (decimal).")
    informationRatio1y: Optional[float] = Field(None, description="Trailing 1-year information ratio.")
    sharpeRatio1y: Optional[float] = Field(None, description="Trailing 1-year Sharpe ratio.")
    sortinoRatio1y: Optional[float] = Field(None, description="Trailing 1-year Sortino ratio.")
    maxDrawdown3y: Optional[float] = Field(None, description="Maximum drawdown over the trailing 3 years (decimal, negative).")
    volatility1y: Optional[float] = Field(None, description="Trailing 1-year realised volatility (decimal).")
    volatility3y: Optional[float] = Field(None, description="Trailing 3-year realised volatility (decimal).")

class TaxStatuses(BaseModel):
    """
    Jurisdiction-specific tax status overlays.
    """
    germanInvestmentTaxAct: Optional[GermanInvTaxAct] = Field(None, description="German Investmentsteuergesetz (InvStG) classification.")
    ukReportingFundStatus: Optional[UkReportingFundStatus] = Field(None, description="UK HMRC Reporting Fund status.")
    frenchPeaEligible: Optional[bool] = Field(None, description="True if eligible for a French PEA.")
    swissDa1Eligible: Optional[bool] = Field(None, description="True if eligible for Swiss DA-1 (withholding tax reclaim).")
    usPfic: Optional[bool] = Field(None, description="True if treated as a PFIC for US tax purposes.")

class GermanInvTaxAct(BaseModel):
    """
    German InvStG fund-category and partial-exemption (Teilfreistellung).
    """
    fundCategory: Optional[str] = Field(None, description="InvStG fund category.")
    teilfreistellungPct: Optional[float] = Field(None, description="Partial exemption rate (decimal) applied to taxable income.")

class UkReportingFundStatus(BaseModel):
    """
    UK HMRC Reporting Fund regime status.
    """
    isReportingFund: Optional[bool] = Field(None, description="True if the share class has UK Reporting Fund status.")
    effectiveDate: Optional[date] = Field(None, description="Date the Reporting Fund status became effective.")

class SubFund(BaseModel):
    """
    Sub-fund-level metadata inside the umbrella.
    """
    name: Optional[str] = Field(None, description="Name of the sub-fund.")
    inceptionDate: Optional[date] = Field(None, description="Inception date of the sub-fund.")

class ShareClass(BaseModel):
    """
    Share-class-level metadata. The share class is the entity actually identified by the document's top-level `isin`; the fields below provide explicit semantics rather than relying on flat scalars at the top level.

    """
    name: Optional[str] = Field(None, description="Display name of the share class (e.g., \"USD Acc\").")
    type: Optional[str] = Field(None, description="Income / distribution / hedging variant of the share class.")
    isin: str = Field(..., description="ISO 6166 ISIN of this share class (same as top-level `isin`).")
    currency: Optional[Currency] = Field(None, description="Currency of the share class.")
    hedged: Optional[bool] = Field(None, description="True if this share class hedges currency exposure.")
    inceptionDate: Optional[date] = Field(None, description="Inception date of the share class.")

class CryptoAsset(FinancialInstrument):
    """
    Crypto-based financial asset (token, coin, digital asset).
    """
    issuer: Optional[List[Issuer]] = Field(None, description="The legal entity that is contractually responsible for the rights or obligations embedded in this instrument. ")
    ticker: Optional[str] = Field(None, description="Symbol/ticker of the crypto asset (e.g., BTC, ETH).")
    network: Optional[str] = Field(None, description="Native blockchain network where the asset is issued.")
    contractAddress: Optional[str] = Field(None, description="Smart contract address for tokenized assets on the network.")
    tokenStandard: Optional[str] = Field(None, description="Token standard or protocol used by the asset (e.g., ERC-20, ERC-1404).")
    decimals: Optional[int] = Field(None, description="Decimal precision defined by the token contract.")
    walletAddress: Optional[str] = Field(None, description="Wallet address holding the raw_data for custody or valuation.")
    custodyType: Optional[str] = Field(None, description="Custody model used to store the asset (e.g., hot wallet, cold storage).")
    isStakable: Optional[bool] = Field(None, description="Indicates whether the asset supports staking.")
    supplyMetrics: Optional[SupplyMetrics] = Field(None, description="Supply and market capitalization metrics for the asset.")
    assetClassification: Optional[str] = Field(None, description="Classification of the asset (e.g., COIN, UTILITY_TOKEN, SECURITY_TOKEN).")
    underlyingAsset: Optional[UnderlyingAsset] = Field(None, description="Details about the underlying asset represented by a security token.")
    complianceRules: Optional[ComplianceRules] = Field(None, description="Compliance and transfer restrictions for security tokens.")
    economicRights: Optional[EconomicRights] = Field(None, description="Economic rights embedded in the token (entitlements, liquidation).")
    governance: Optional[Governance] = Field(None, description="Governance and voting rights for the token.")

class SupplyMetrics(BaseModel):
    """
    Supply and market capitalization data for a crypto asset.
    """
    circulatingSupply: Optional[float] = Field(None, description="Number of tokens currently in public circulation.")
    totalSupply: Optional[float] = Field(None, description="Total number of tokens minted to date.")
    maxSupply: Optional[float] = Field(None, description="Maximum number of tokens that can ever be created.")
    marketCap: Optional[float] = Field(None, description="Market capitalization (price times circulating supply).")

class UnderlyingAsset(BaseModel):
    """
    Reference to the underlying asset represented by a security token.
    """
    category: Optional[str] = Field(None, description="Asset category (e.g., REAL_ESTATE, EQUITY, DEBT).")
    assetReference: Optional[str] = Field(None, description="Reference identifier for the underlying asset.")
    valuationMethod: Optional[str] = Field(None, description="Valuation method used for the underlying asset.")

class ComplianceRules(BaseModel):
    """
    Regulatory identifiers and compliance rules for a security token.
    """
    registrationStatus: Optional[str] = Field(None, description="Registration status with a regulator.")
    restrictedPersonList: Optional[str] = Field(None, description="Description or reference to restricted persons list.")
    whitelistId: Optional[str] = Field(None, description="Identifier for the KYC/AML whitelist registry.")
    kycRequired: Optional[bool] = Field(None, description="Indicates whether KYC is required for holding the token.")
    investorTypeAllowed: Optional[List[str]] = Field(None, description="Allowed investor types for holding the token.")
    prohibitedJurisdictions: Optional[List[Country]] = Field(None, description="Jurisdictions where holding/transfers are prohibited.")
    transferRestrictedUntil: Optional[date] = Field(None, description="Date until which transfers are restricted or locked.")

class EconomicRights(BaseModel):
    """
    Economic entitlements embedded in the token.
    """
    entitlements: Optional[List[str]] = Field(None, description="Rights to dividends, interest payments, or liquidation proceeds.")
    liquidationPreference: Optional[str] = Field(None, description="Priority of token holders in liquidation scenarios.")

class Governance(BaseModel):
    """
    Governance and voting parameters for a security token.
    """
    hasVotingRights: Optional[bool] = Field(None, description="Whether token holders have voting rights.")
    votingWeight: Optional[float] = Field(None, description="Voting weight per token.")
    proposalRights: Optional[str] = Field(None, description="Rights to initiate governance proposals.")
    dividendPolicy: Optional[str] = Field(None, description="Dividend or distribution policy for token holders.")

class Commodity(FinancialInstrument):
    """
    Commodity financial instrument.
    """
    unitOfMeasure: Optional[str] = Field(None, description="Unit of measure used to quote the commodity (e.g., OZT, BBL, MT).")
    contractSize: Optional[ContractSize] = Field(None, description="Contract size or multiplier for derivative exposure.")
    quoteCurrency: Optional[Currency] = Field(None, description="Currency in which the commodity is quoted (usually USD).")
    priceFactor: Optional[float] = Field(None, description="Factor applied to unit price for valuation (typically 1.0).")
    purity: Optional[str] = Field(None, description="Purity or grade of the commodity (e.g., 0.9999 for gold).")
    custodyModel: Optional[str] = Field(None, description="Custody or ownership model for the commodity raw_data.")
    isAllocated: Optional[bool] = Field(None, description="Indicates whether the commodity is held in allocated custody.")
    safeCustody: Optional[bool] = Field(None, description="Indicates whether the commodity is held in safe custody.")
    storageLocation: Optional[str] = Field(None, description="Storage or vault location identifier for physical holdings.")
    valuation: Optional[CommodityValuation] = Field(None, description="Valuation attributes for the commodity instrument.")
    costs: Optional[CommodityCosts] = Field(None, description="Storage and insurance cost attributes for the commodity.")
    lifecycle: Optional[CommodityLifecycle] = Field(None, description="Lifecycle metadata for commodity contracts.")

class CommodityValuation(BaseModel):
    """
    Valuation attributes for a commodity instrument.
    """
    quantity: Optional[Quantity] = Field(None, description="Quantity of the commodity held.")
    unitPrice: Optional[Price] = Field(None, description="Unit price of the commodity.")
    priceCurrency: Optional[Currency] = Field(None, description="Currency used for commodity pricing.")
    marketValueBase: Optional[CurrencyAmount] = Field(None, description="Market value converted to the base currency.")

class CommodityCosts(BaseModel):
    """
    Cost of carry, storage, and insurance attributes for a commodity.
    """
    annualStorageFeePct: Optional[float] = Field(None, description="Annual storage fee expressed as a percentage.")
    accruedStorageFees: Optional[CurrencyAmount] = Field(None, description="Accrued storage fees not yet settled.")
    storageRate: Optional[float] = Field(None, description="Storage rate or flat fee applied to the physical holding.")
    insuranceFee: Optional[CurrencyAmount] = Field(None, description="Insurance fee for protecting the physical asset.")
    lastPhysicalInspectionDate: Optional[date] = Field(None, description="Date of the last physical inspection or audit.")

class CommodityLifecycle(BaseModel):
    """
    Lifecycle metadata for commodity contracts.
    """
    expiryDate: Optional[date] = Field(None, description="Expiry date of the commodity contract.")
    rollSchedule: Optional[str] = Field(None, description="Roll schedule or rules for contract rollover.")

class Rating(BaseModel):
    """
    A credit rating assigned by an agency.
    """
    agency: Optional[str] = Field(None, description="The credit rating agency (e.g., S&P, Moody's, Fitch).")
    rating: Optional[str] = Field(None, description="The assigned rating symbol (e.g., AAA, Baa1).")
    ratingType: Optional[str] = Field(None, description="The type of rating (e.g., issuer_credit_rating, issue_credit_rating).")
    outlook: Optional[str] = Field(None, description="The rating outlook (e.g., stable, positive, negative).")
    scale: Optional[str] = Field(None, description="The rating scale (e.g., long_term, short_term).")
    dateAssigned: Optional[date] = Field(None, description="The date when the rating was assigned.")
    status: Optional[str] = Field(None, description="The status of the rating (e.g., active, withdrawn).")

class CreditProfile(BaseModel):
    """
    Creditworthiness profile of an issuer.
    """
    issuerRatings: Optional[List[Rating]] = Field(None, description="List of ratings assigned to the issuer.")

class CreditRisk(BaseModel):
    """
    Credit risk profile of a specific financial instrument.
    """
    instrumentRatings: Optional[List[Rating]] = Field(None, description="List of ratings assigned to the instrument.")
    recoveryAssumptions: Optional[RecoveryAssumptions] = Field(None, description="Assumptions about recovery in case of default.")

class RecoveryAssumptions(BaseModel):
    """
    Recovery and notching details.
    """
    agency: Optional[str] = Field(None, description="The agency providing the recovery assessment.")
    recoveryRating: Optional[str] = Field(None, description="Recovery rating (e.g., 1 to 6).")
    expectedRecoveryPercent: Optional[str] = Field(None, description="Expected recovery percentage range.")
    methodology: Optional[str] = Field(None, description="The methodology used for the assessment.")

class ESGProvider(BaseModel):
    """
    Information about the entity providing ESG assessments.
    """
    providerId: Optional[str] = Field(None, description="Unique identifier for the provider (e.g., MSCI, Sustainalytics).")
    legalName: Optional[str] = Field(None, description="Legal name of the provider.")
    methodologyVersion: Optional[str] = Field(None, description="Version of the methodology used for the rating.")
    ratingScale: Optional[str] = Field(None, description="Description of the rating scale used (e.g., AAA-CCC, 0-100).")
    website: Optional[str] = Field(None, description="Official website of the provider.")

class ESGPillarScore(BaseModel):
    """
    Score for an individual ESG pillar (Environmental, Social, or Governance).
    """
    pillar: Optional[str] = Field(None, description="The ESG pillar being scored.")
    scoreValue: Optional[str] = Field(None, description="The score value assigned to this pillar.")
    scale: Optional[str] = Field(None, description="The scale used for this pillar score.")

class ESGCompositeScore(BaseModel):
    """
    The overall composite ESG score.
    """
    scoreValue: Optional[str] = Field(None, description="The composite score value.")
    scale: Optional[str] = Field(None, description="The scale used for the composite score.")
    confidenceLevel: Optional[float] = Field(None, description="Optional confidence level of the score.")

class ESGAssessment(BaseModel):
    """
    A specific ESG assessment by a provider at a point in time.
    """
    assessmentId: Optional[str] = Field(None, description="Unique identifier for the assessment.")
    providerRef: Optional[ESGProvider] = Field(None, description="Reference to the ESG provider.")
    assessmentDate: Optional[date] = Field(None, description="The date when the assessment was performed.")
    coverageScope: Optional[str] = Field(None, description="Whether the assessment covers the issuer or a specific instrument.")
    methodologyVersion: Optional[str] = Field(None, description="Version of the methodology used.")
    pillars: Optional[List[ESGPillarScore]] = Field(None, description="Pillar-level scores.")
    composite: Optional[ESGCompositeScore] = Field(None, description="Overall composite score.")
    controversies: Optional[ESGControversies] = Field(None, description="Information about ESG controversies.")
    source: Optional[ESGSource] = Field(None, description="Information about the data source.")

class ESGControversies(BaseModel):
    """
    Information about ESG controversies.
    """
    level: Optional[str] = Field(None, description="The severity level of controversies.")
    lastUpdated: Optional[date] = Field(None, description="The date when the controversy information was last updated.")

class ESGSource(BaseModel):
    """
    Information about the data source for the assessment.
    """
    sourceType: Optional[str] = Field(None, description="The type of data source.")
    disclosureYear: Optional[int] = Field(None, description="The year of the underlying disclosures.")

class ESGProfile(BaseModel):
    """
    ESG profile containing multiple assessments.
    """
    esgAssessments: Optional[List[ESGAssessment]] = Field(None, description="List of ESG assessments.")

class ESGInheritanceRule(BaseModel):
    """
    Rules for inheriting ESG properties from an issuer.
    """
    defaultBehavior: Optional[str] = Field(None, description="The default inheritance behavior.")
    overrideAllowed: Optional[bool] = Field(None, description="Whether the inherited values can be overridden.")
    overrideScope: Optional[str] = Field(None, description="The scope of the allowed override.")

class ESGInstrumentOverlay(BaseModel):
    """
    Instrument-specific ESG metadata that overlays issuer ESG.
    """
    overlayType: Optional[str] = Field(None, description="The type of ESG overlay.")
    standardReference: Optional[ESGStandardReference] = Field(None, description="Reference to industry standards or frameworks.")
    useOfProceeds: Optional[ESGUseOfProceeds] = Field(None, description="Information on the use of proceeds.")
    reportingCommitments: Optional[ESGReportingCommitments] = Field(None, description="Commitments to reporting.")
    instrumentSpecificAssessment: Optional[ESGAssessment] = Field(None, description="Assessment specific to this instrument.")

class ESGStandardReference(BaseModel):
    """
    Reference to ESG standards or frameworks.
    """
    framework: Optional[str] = Field(None, description="The framework or standard being followed.")

class ESGUseOfProceeds(BaseModel):
    """
    Details on the use of proceeds for an instrument.
    """
    eligibleCategories: Optional[List[str]] = Field(None, description="Categories of projects eligible for funding.")
    exclusionCategories: Optional[List[str]] = Field(None, description="Categories of projects excluded from funding.")

class ESGReportingCommitments(BaseModel):
    """
    Reporting commitments for an ESG instrument.
    """
    allocationReporting: Optional[bool] = Field(None, description="Commitment to report on the allocation of funds.")
    impactReporting: Optional[bool] = Field(None, description="Commitment to report on the impact of the projects.")

class ESGInstrumentProfile(BaseModel):
    """
    ESG profile for a financial instrument.
    """
    inheritanceRule: Optional[ESGInheritanceRule] = Field(None, description="Rules for ESG inheritance from the issuer.")
    inheritedAssessments: Optional[ESGInheritedAssessments] = Field(None, description="Configuration for inherited assessments.")
    instrumentOverlays: Optional[List[ESGInstrumentOverlay]] = Field(None, description="List of instrument-specific ESG overlays.")

class ESGInheritedAssessments(BaseModel):
    """
    Configuration for inherited ESG assessments.
    """
    fromIssuer: Optional[bool] = Field(None, description="Whether to inherit from the issuer.")
    providerPriority: Optional[List[str]] = Field(None, description="Priority list of providers for inherited assessments.")

class Cash(FinancialInstrument):
    """
    Cash financial instrument.
    """
    baseCurrency: Optional[Currency] = Field(None, description="Base currency of the portfolio used for valuation.")
    localCurrency: Optional[Currency] = Field(None, description="Currency of the cash instrument itself.")
    fxRateToBase: Optional[float] = Field(None, description="FX rate applied to convert local currency values into the base currency.")
    balance: Optional[CashBalance] = Field(None, description="Balance details for the cash raw_data.")
    valuation: Optional[CashValuation] = Field(None, description="Valuation attributes for the cash instrument.")
    yieldDetails: Optional[CashYieldDetails] = Field(None, description="Interest and yield attributes for the cash raw_data.")
    assetClassCategory: Optional[str] = Field(None, description="Asset class categorization for the cash raw_data.")
    isCollateral: Optional[bool] = Field(None, description="Indicates whether the cash raw_data is used as collateral.")
    isSweepable: Optional[bool] = Field(None, description="Indicates whether excess cash is automatically swept into a higher-yield vehicle.")
    isOverdraft: Optional[bool] = Field(None, description="Indicates whether the cash raw_data represents a negative balance.")
    overdraftAllowed: Optional[bool] = Field(None, description="Indicates whether overdraft is permitted for the cash raw_data.")
    overdraftLimit: Optional[CurrencyAmount] = Field(None, description="Maximum overdraft limit available for the cash raw_data.")
    settlementDetails: Optional[CashSettlementDetails] = Field(None, description="Settlement-related attributes for the cash instrument.")

class CashBalance(BaseModel):
    """
    Balance components for a cash raw_data.
    """
    bookBalance: Optional[CurrencyAmount] = Field(None, description="Total amount of cash in the account.")
    availableBalance: Optional[CurrencyAmount] = Field(None, description="Amount of cash that is immediately available to spend or withdraw.")
    blockedAmount: Optional[CurrencyAmount] = Field(None, description="Portion of the balance that is blocked or reserved.")

class CashValuation(BaseModel):
    """
    Valuation attributes for cash instruments.
    """
    quantity: Optional[Quantity] = Field(None, description="Cash quantity held in the local currency.")
    unitPrice: Optional[Price] = Field(None, description="Unit price of the cash instrument in the local currency.")
    marketValueBase: Optional[CurrencyAmount] = Field(None, description="Market value converted into the base currency.")
    valueDate: Optional[date] = Field(None, description="Date used for interest calculation and valuation.")
    transactionDate: Optional[date] = Field(None, description="Date the transaction was initiated.")

class CashYieldDetails(BaseModel):
    """
    Yield and interest metadata for a cash instrument.
    """
    creditInterestRate: Optional[InterestRate] = Field(None, description="Interest rate applied to positive cash balances.")
    debitInterestRate: Optional[InterestRate] = Field(None, description="Interest rate applied to negative cash balances (overdraft).")
    accruedInterest: Optional[CurrencyAmount] = Field(None, description="Interest accrued but not yet capitalized.")
    lastInterestCapitalizationDate: Optional[date] = Field(None, description="Date when interest was last capitalized.")

class CashSettlementDetails(BaseModel):
    """
    Settlement and account metadata for a cash instrument.
    """
    settlementCycle: Optional[str] = Field(None, description="Settlement cycle for cash movements (e.g., T+0, T+1).")
    custodian: Optional[str] = Field(None, description="Custodian or servicing entity for the cash account.")
    accountIban: Optional[str] = Field(None, description="IBAN of the cash account if applicable.")
    accountNumber: Optional[str] = Field(None, description="Proprietary account number for the cash raw_data.")
    nostroVostroIndicator: Optional[str] = Field(None, description="Indicator whether the cash is held as nostro or vostro.")

class Equity(FinancialInstrument):
    """
    Equity financial instrument.
    """
    issuer: Optional[List[Issuer]] = Field(None, description="The legal entity that is contractually responsible for the rights or obligations embedded in this instrument. ")
    tickerSymbol: Optional[str] = Field(None, description="Exchange-specific ticker symbol for the equity.")
    exchangeMic: Optional[str] = Field(None, description="Market Identifier Code (MIC) of the primary exchange.")
    shareClass: Optional[str] = Field(None, description="Share class (e.g., Class A, Class B, Preferred).")
    equitySubType: Optional[str] = Field(None, description="Equity sub-type capturing the legal/structural variant of the share (Common, Preferred, ADR/GDR, REIT, MLP, Convertible Preferred, etc.). ")
    sharesOutstanding: Optional[float] = Field(None, description="Total shares currently issued and outstanding.")
    firstTradingDate: Optional[date] = Field(None, description="Date the equity was first admitted to trading.")
    delistingDate: Optional[date] = Field(None, description="Date of delisting, if applicable.")
    lifecycleStatus: Optional[str] = Field(None, description="Lifecycle status of the equity instrument.")
    parValue: Optional[CurrencyAmount] = Field(None, description="Nominal par value stated in the corporate charter.")
    votingRatio: Optional[float] = Field(None, description="Number of votes per share.")
    hasVotingRights: Optional[bool] = Field(None, description="Indicates whether the equity carries voting rights.")
    incorporationCountry: Optional[Country] = Field(None, description="Country of incorporation of the issuing company.")
    currencyOfDenomination: Optional[Currency] = Field(None, description="Currency in which the equity is denominated.")
    industrySector: Optional[IndustrySector] = Field(None, description="Industry/sector classification of the issuing company.")
    dividendStatus: Optional[bool] = Field(None, description="Indicates whether the equity currently pays dividends.")
    dividendPolicy: Optional[DividendPolicy] = Field(None, description="Dividend policy details for the equity.")
    keyFigures: Optional[KeyFigures] = Field(None, description="Key valuation figures related to the equity.")
    marketData: Optional[MarketData] = Field(None, description="Dynamic market data points for the equity.")

class DividendPolicy(BaseModel):
    """
    Dividend policy details for an equity instrument.
    """
    dividendYield: Optional[float] = Field(None, description="Last reported dividend yield (decimal or percent).")
    lastDividendDate: Optional[date] = Field(None, description="Date of the last dividend payment.")
    frequency: Optional[str] = Field(None, description="Dividend frequency (e.g., annual, quarterly).")

class KeyFigures(BaseModel):
    """
    Key valuation figures for an equity instrument.
    """
    marketCapitalization: Optional[CurrencyAmount] = Field(None, description="Total market value of the company's outstanding shares.")
    earningsPerShare: Optional[CurrencyAmount] = Field(None, description="Company's profit divided by the outstanding shares.")
    priceToEarningsRatio: Optional[float] = Field(None, description="Price-to-earnings ratio (P/E).")
    volatility: Optional[float] = Field(None, description="Equity price volatility measure (e.g., historical or implied).")

class MarketData(BaseModel):
    """
    Market data fields for an equity instrument.
    """
    lastTradePrice: Optional[Price] = Field(None, description="Most recent price at which the equity traded.")
    marketCapCategory: Optional[str] = Field(None, description="Market capitalization category (e.g., Large-Cap, Mid-Cap, Small-Cap).")

class Fund(FinancialInstrument):
    """
    Investment fund (mutual fund, ETF, etc.).
    """
    issuer: Optional[List[Issuer]] = Field(None, description="The legal entity that is contractually responsible for the rights or obligations embedded in this instrument. ")
    instrumentEsgProfile: Optional[ESGInstrumentProfile] = Field(None, description="ESG profile of the fund, allowing instrument-specific overlays.")
    holdingsCount: Optional[int] = Field(None, description="Total number of individual securities held within the fund's portfolio.")
    isCurrencyHedged: Optional[bool] = Field(None, description="Indicates whether the fund (or specific share class) employs a currency hedging strategy to reduce FX risk.")
    hedgingCurrency: Optional[Currency] = Field(None, description="The target currency into which the fund's underlying exposures are hedged.")
    assetAllocation: Optional[AssetAllocation] = Field(None, description="Breakdown of the fund's holdings by allocation buckets (e.g., asset class, region, industry_sector) including look-through top holdings.")
    dividendPolicy: Optional[str] = Field(None, description="Specifies how the fund handles income (dividends, interest). DISTRIBUTING: pays out income to investors. ACCUMULATING: reinvests income back into the fund. ")
    fees: Optional[FundFeeStructure] = Field(None, description="Detailed fee structure of the investment fund, including ongoing, transactional, and incentive-based costs.")
    legalFramework: Optional[str] = Field(None, description="The regulatory framework governing the fund (e.g., UCITS, AIFMD, 40-Act). UCITS is a common European standard for retail funds. ")
    legalStructure: Optional[str] = Field(None, description="The specific legal form of the fund entity (e.g., SICAV, ICAV, FCP, LP). This defines whether the fund is a company or a contractual arrangement. ")
    umbrellaName: Optional[str] = Field(None, description="The name of the legal umbrella entity that contains one or more sub-funds. Common in European structures where multiple funds share a single prospectus. ")
    domicile: Optional[str] = Field(None, description="The country where the fund is legally registered and regulated.")

class FundFeeStructure(BaseModel):
    """
    Structure representing various types of fees associated with an investment fund.
    """
    ongoing: Optional[OngoingFees] = Field(None, description="Fees deducted from the fund's assets and reflected in the NAV.")
    transactional: Optional[TransactionalFees] = Field(None, description="Fees occurring at the point of entry or exit.")
    incentive: Optional[IncentiveFees] = Field(None, description="Fees based on performance benchmarks, common in hedge funds.")
    taxWrapperCosts: Optional[TaxWrapperCosts] = Field(None, description="Internal tax-related costs within the fund structure.")

class OngoingFees(BaseModel):
    """
    Fees deducted from the fund's assets and reflected in the NAV.
    """
    totalExpenseRatio: Optional[float] = Field(None, description="The Total Expense Ratio (TER) represents the annual percentage fee charged to cover management and operating costs. ")
    managementFee: Optional[float] = Field(None, description="The specific annual fee paid to the portfolio manager.")
    adminFee: Optional[float] = Field(None, description="Operational costs such as legal and audit fees.")
    isCapped: Optional[bool] = Field(None, description="Indicates whether the fees are capped at a certain percentage.")

class TransactionalFees(BaseModel):
    """
    Fees occurring when moving money in or out of the fund.
    """
    entryLoad: Optional[float] = Field(None, description="Fee paid when joining the fund.")
    exitLoad: Optional[float] = Field(None, description="Fee paid when leaving the fund.")
    buySellSpreadEst: Optional[float] = Field(None, description="Estimated spread between buy and sell prices.")

class IncentiveFees(BaseModel):
    """
    Performance-based fees for the fund manager.
    """
    performanceFee: Optional[float] = Field(None, description="Percentage of profits taken by the manager for exceeding targets.")
    hurdleRate: Optional[float] = Field(None, description="Target return rate that must be exceeded before performance fees apply.")
    highWaterMark: Optional[bool] = Field(None, description="Ensures fees are only paid on new profits, not on recovery from past losses.")

class TaxWrapperCosts(BaseModel):
    """
    Internal tax-related costs within the fund structure.
    """
    stampDuty: Optional[float] = Field(None, description="Tax on the purchase of the fund or its underlying assets.")
    withholdingTaxInternal: Optional[str] = Field(None, description="Internal withholding tax (e.g., on dividends).")

class AssetAllocation(BaseModel):
    """
    Asset allocation of a fund, expressed as percentage weights across different dimensions. Percentages should typically sum to 1.0 within each dimension.

    """
    byAssetClass: Optional[List[Dict[str, Any]]] = Field(None, description="Allocation by asset class (the \"what\").")
    byRegion: Optional[List[Dict[str, Any]]] = Field(None, description="Allocation by region (the \"where\").")
    bySector: Optional[List[Dict[str, Any]]] = Field(None, description="Allocation by industry_sector (the \"industry\"), mainly for equity exposure.")
    holdings: Optional[List[Holding]] = Field(None, description="Look-through data: the underlying holdings of the fund, each with an identifier, name and portfolio weight. The array can be a \"top N\" projection (when the source is yfinance / a fact-sheet) or the full constituent list (when the source is an issuer holdings parser or daily CSV). The total constituent count is recorded in `holdingsCount` at the FundGolden level, separate from `len(holdings)`. ")

class Holding(BaseModel):
    """
    A single underlying holding within a fund's look-through holdings list. The list can be a top-N projection or the full constituent list — see `FundGolden.holdings` / `holdingsCount` for the source and total count.

    """
    identifier: str = Field(..., description="Security identifier of the underlying holding (e.g., ISIN or ticker).")
    name: str = Field(..., description="Human-readable name of the underlying holding.")
    weight: float = Field(..., description="Weight of this holding as a decimal (e.g., 0.071 for 7.1%).")
    assetClass: Optional[str] = Field(None, description="Asset class of the holding (e.g., EQUITY, FIXED_INCOME, DERIVATIVE, CASH).")
    source: Optional[str] = Field(None, description="Provenance of this row. `direct` (default for back-compat) = from the issuer's own holdings page or factsheet. `physical_proxy` = copied from a physically-replicated ETF tracking the same benchmark (used for swap-based ETFs whose own holdings page returns the substitute basket, not the economic exposure). The other values are reserved for future strategies. ")

class LookthroughProvenance(BaseModel):
    """
    Provenance metadata for proxy-derived look-through holdings. Populated only when `assetAllocation.holdings` carries rows whose `source` is not `direct`. Null otherwise.

    """
    method: str = Field(..., description="Strategy used to derive look-through holdings indirectly.")
    proxyIsin: str = Field(..., description="ISIN of the proxy fund whose holdings were copied.")
    proxyGoldenId: Optional[str] = Field(None, description="goldenId of the proxy fund record in pms_golden_fund.")
    proxyName: Optional[str] = Field(None, description="Human-readable name of the proxy fund.")
    benchmarkIdentifier: Optional[str] = Field(None, description="Identifier of the benchmark linking target fund and proxy.")
    benchmarkName: str = Field(..., description="Name of the benchmark linking target fund and proxy.")
    asOfDate: date = Field(..., description="Snapshot date of the proxy's holdings (carried through verbatim).")
    confidence: str = Field(..., description="Match quality. `high` = identifier exact match; `medium` = benchmark name match but different identifier (variant index); `low` = fuzzy / substring name match only. ")

class MultiBarrierReverseConvertible(FinancialInstrument):
    """
    Multi-asset barrier reverse convertible structured product.
    """
    basket: Optional[BasketDefinition] = Field(None, description="Reference to the basket definition of underlying assets.")
    basketId: Optional[str] = Field(None, description="Legacy basket identifier linking to external systems.")
    couponRate: Optional[Decimal] = Field(None, description="Guaranteed annual coupon rate paid regardless of barrier events.")
    issuer: Optional[List[Issuer]] = Field(None, description="Entity responsible for the fixed coupon and principal return.")
    maturityDate: Optional[date] = Field(None, description="Final settlement date of the product.")
    worstOfLogic: Optional[bool] = Field(None, description="Indicates whether worst-of logic applies to basket performance.")
    barrierLevel: Optional[Decimal] = Field(None, description="Barrier threshold expressed as a percentage of the initial fixing.")
    correlationFactor: Optional[Decimal] = Field(None, description="Statistical relationship between basket assets used for valuation.")
    strikePrice: Optional[Price] = Field(None, description="Reference strike price for each basket asset.")
    physicalDelivery: Optional[str] = Field(None, description="Identifies which asset is delivered upon a physical settlement trigger.")

class BarrierReverseConvertible(FinancialInstrument):
    """
    Barrier reverse convertible structured product.
    """
    issuer: Optional[List[Issuer]] = Field(None, description="Financial institution issuing and guaranteeing the product.")
    couponRate: Optional[Decimal] = Field(None, description="Guaranteed annual coupon rate paid regardless of barrier events.")
    denomination: Optional[CurrencyAmount] = Field(None, description="Face value per unit of the product.")
    maturityDate: Optional[date] = Field(None, description="Final date of the contract and principal repayment.")
    underlyingFinancialInstrument: Optional[FinancialInstrument] = Field(None, description="Reference underlying asset for the barrier observation.")
    strikePrice: Optional[Price] = Field(None, description="Strike price level, typically set at the initial fixing price.")
    barrierLevel: Optional[Decimal] = Field(None, description="Barrier threshold as a percentage or level of the initial price.")
    barrierType: Optional[str] = Field(None, description="Barrier observation type (continuous or European).")
    barrierEvent: Optional[bool] = Field(None, description="Indicates whether the barrier has been breached.")
    settlementType: Optional[str] = Field(None, description="Settlement method at maturity (cash or physical delivery).")

class Option(FinancialInstrument):
    """
    Generic option financial instrument.
    """
    expiryDate: Optional[date] = Field(None, description="Expiry date of the option.")
    exercisePrice: Optional[Price] = Field(None, description="Exercise (strike) price of the option.")
    contractSize: Optional[ContractSize] = Field(None, description="Contract size specifying standardized units.")
    optionType: Optional[OptionType] = Field(None, description="Type of option (call/put).")
    optionStyle: Optional[OptionStyle] = Field(None, description="Exercise style of the option (European/American/etc.).")
    underlyingFinancialInstrument: Optional[FinancialInstrument] = Field(None, description="The underlying financial instrument on which the option is written.")

class CallOption(Option):
    """
    A call option gives the holder the right to buy the underlying.
    """
    pass

class PutOption(Option):
    """
    A put option gives the holder the right to sell the underlying.
    """
    pass

class Future(FinancialInstrument):
    """
    Future contract based on an underlying financial instrument.
    """
    expiryDate: Optional[date] = Field(None, description="Expiry date of the future contract.")
    expiryCode: Optional[ExpiryCode] = Field(None, description="Contract expiry code representing the delivery month and year.")
    contractSize: Optional[ContractSize] = Field(None, description="Contract size specifying standardized units.")
    tickSize: Optional[TickSize] = Field(None, description="Minimum price fluctuation allowed for the future contract.")
    initialMargin: Optional[CurrencyAmount] = Field(None, description="Initial margin required to open the future raw_data.")
    maintenanceMargin: Optional[CurrencyAmount] = Field(None, description="Minimum margin required to keep the future raw_data open.")
    underlyingFinancialInstrument: Optional[FinancialInstrument] = Field(None, description="Underlying financial instrument the future derives from.")
    tickerSymbol: Optional[str] = Field(None, description="Exchange-specific ticker symbol of the future.")
    exercisePrice: Optional[Price] = Field(None, description="Exercise (strike) price of the future.")

class FxForward(FinancialInstrument):
    """
    Foreign exchange forward contract.
    """
    currencyPair: Optional[CurrencyPair] = Field(None, description="Currency pair for the FX forward (base/quote).")
    counterpartyLei: Optional[LegalEntityIdentifier] = Field(None, description="Legal Entity Identifier (LEI) of the counterparty.")
    counterpartyName: Optional[str] = Field(None, description="Legal name of the counterparty.")
    amountPaid: Optional[CurrencyAmount] = Field(None, description="Currency amount paid in the FX forward.")
    amountReceived: Optional[CurrencyAmount] = Field(None, description="Currency amount received in the FX forward.")
    nearAmount: Optional[CurrencyAmount] = Field(None, description="Amount of the base currency exchanged at the forward rate.")
    nearCurrency: Optional[Currency] = Field(None, description="ISO 4217 code of the base currency.")
    forwardRate: Optional[ForwardRate] = Field(None, description="Agreed forward exchange rate.")
    valueDate: Optional[date] = Field(None, description="Value (settlement) date of the FX forward.")
    maturityDate: Optional[date] = Field(None, description="Maturity (settlement) date of the FX forward.")
    creditSupport: Optional[CreditSupport] = Field(None, description="Credit support or collateral agreement (e.g., CSA).")
    isDeliverable: Optional[bool] = Field(None, description="Indicates whether the FX forward is physically deliverable.")

class FxOption(FinancialInstrument):
    """
    Foreign exchange option contract.
    """
    optionType: Optional[OptionType] = Field(None, description="Type of option (call/put).")
    optionStyle: Optional[OptionStyle] = Field(None, description="Exercise style of the option (European/American/etc.).")
    currencyPair: Optional[CurrencyPair] = Field(None, description="Currency pair for the FX option (base/quote).")
    counterpartyLei: Optional[LegalEntityIdentifier] = Field(None, description="Legal Entity Identifier (LEI) of the option writer/seller.")
    strikePrice: Optional[Price] = Field(None, description="Strike price (exchange rate) at which the option can be exercised.")
    notionalAmount: Optional[CurrencyAmount] = Field(None, description="Notional amount of the currency protected by the option.")
    premium: Optional[CurrencyAmount] = Field(None, description="Premium paid to purchase the FX option.")
    expiryDate: Optional[date] = Field(None, description="Expiry date of the FX option.")
    settlementDate: Optional[date] = Field(None, description="Settlement date for the FX option.")

class CreditDefaultSwap(FinancialInstrument):
    """
    Credit default swap financial instrument.
    """
    notionalAmount: Optional[CurrencyAmount] = Field(None, description="Notional amount of the CDS contract.")
    referenceEntityName: Optional[str] = Field(None, description="Legal name of the reference entity whose credit risk is insured.")
    referenceEntityIdentifier: Optional[str] = Field(None, description="Identifier of the reference entity (e.g., LEI or RED code).")
    referenceObligation: Optional[str] = Field(None, description="Reference obligation identifier (e.g., ISIN of the benchmark bond).")
    seniority: Optional[str] = Field(None, description="Seniority level of the reference obligation.")
    cdsSpreadBps: Optional[float] = Field(None, description="CDS spread quoted in basis points per year.")
    effectiveDate: Optional[date] = Field(None, description="Date when protection starts.")
    maturityDate: Optional[date] = Field(None, description="Maturity date of the CDS.")
    paymentFrequency: Optional[str] = Field(None, description="Frequency of premium payments.")
    settlementMethod: Optional[str] = Field(None, description="Settlement method applied upon a credit event.")
    businessDayConvention: Optional[str] = Field(None, description="Business day convention for adjusting payment dates.")
    fixedCoupon: Optional[float] = Field(None, description="Standardized fixed coupon rate for the CDS contract.")
    upfrontPayment: Optional[CurrencyAmount] = Field(None, description="Upfront payment amount to equalize value at trade inception.")
    dayCountConvention: Optional[DayCountBasis] = Field(None, description="Day count convention for premium accruals.")
    restructuringType: Optional[str] = Field(None, description="Restructuring type that qualifies as a credit event.")
    creditEventFailureToPay: Optional[bool] = Field(None, description="Indicates whether failure to pay triggers a credit event.")
    creditEventBankruptcy: Optional[bool] = Field(None, description="Indicates whether bankruptcy triggers a credit event.")
    creditEventAcceleration: Optional[bool] = Field(None, description="Indicates whether acceleration triggers a credit event.")
    marketSpreadBps: Optional[float] = Field(None, description="Current market spread for the CDS in basis points.")
    dv01: Optional[float] = Field(None, description="Risky PV01 measuring value change per 1bp spread move.")
    recoveryRate: Optional[float] = Field(None, description="Assumed recovery rate after default.")
    impliedProbabilityOfDefault: Optional[float] = Field(None, description="Implied probability of default derived from market spreads.")
    accruedPremium: Optional[CurrencyAmount] = Field(None, description="Accrued premium amount since the last payment date.")
    underlyingFinancialInstrument: Optional[FinancialInstrument] = Field(None, description="Underlying financial instrument whose credit risk is transferred.")

class FxSwap(FinancialInstrument):
    """
    Foreign exchange swap contract.
    """
    nearAmount: Optional[CurrencyAmount] = Field(None, description="Amount of the first currency exchanged in the near leg.")
    nearCurrency: Optional[Currency] = Field(None, description="ISO 4217 code for the base currency in the near leg.")
    forwardRate: Optional[ForwardRate] = Field(None, description="Agreed-upon exchange rate for the far leg.")
    valueDate: Optional[date] = Field(None, description="Date of the final payment/exchange (maturity).")
    creditSupport: Optional[CreditSupport] = Field(None, description="Credit support or collateral agreement governing the FX swap.")
    currencyPair: Optional[CurrencyPair] = Field(None, description="Reference currency pair for the FX swap (base/quote).")
    maturityDate: Optional[date] = Field(None, description="Final date for the far-leg delivery.")
    settlementType: Optional[str] = Field(None, description="Settlement method for the FX swap (cash or physical exchange).")
    currency: Optional[Currency] = Field(None, description="ISO 4217 code for the contract pricing currency.")

class TotalReturnSwap(FinancialInstrument):
    """
    Total return swap contract.
    """
    underlyingId: Optional[str] = Field(None, description="Identifier of the underlying asset being swapped.")
    notionalAmount: Optional[CurrencyAmount] = Field(None, description="Face value of the underlying asset protected or swapped.")
    fundingRate: Optional[Decimal] = Field(None, description="Set rate paid to the payer (e.g., SOFR + spread).")
    paymentFrequency: Optional[str] = Field(None, description="Frequency of total return and funding leg settlements.")
    assetPerformance: Optional[Decimal] = Field(None, description="Capital gains/losses plus income generated by the asset.")
    maturityDate: Optional[date] = Field(None, description="Final date the contract remains valid.")
    settlementType: Optional[str] = Field(None, description="Settlement method for the TRS cash flows.")
    initialMargin: Optional[CurrencyAmount] = Field(None, description="Collateral required to open the TRS raw_data.")
    currency: Optional[Currency] = Field(None, description="ISO 4217 code for the TRS cash flows.")
    creditSupport: Optional[CreditSupport] = Field(None, description="Credit support agreement governing collateral management.")

class InterestRateSwap(FinancialInstrument):
    """
    Interest rate swap contract.
    """
    notionalAmount: Optional[CurrencyAmount] = Field(None, description="Notional amount on which swap payments are based.")
    fixedRate: Optional[Decimal] = Field(None, description="Fixed percentage rate paid on the fixed leg.")
    floatingIndex: Optional[str] = Field(None, description="Reference rate index for the floating leg (e.g., LIBOR, SOFR).")
    spread: Optional[Decimal] = Field(None, description="Spread added to the floating index for the floating leg.")
    paymentFrequency: Optional[str] = Field(None, description="Frequency of interest payments.")
    effectiveDate: Optional[date] = Field(None, description="Date interest starts accruing.")
    maturityDate: Optional[date] = Field(None, description="Final date when the swap obligations end.")
    settlementType: Optional[str] = Field(None, description="Settlement method for the swap cash flows.")
    dayCountConvention: Optional[DayCountBasis] = Field(None, description="Day count convention for interest calculation.")
    currency: Optional[Currency] = Field(None, description="ISO 4217 code for swap cash flows.")

class Bond(FinancialInstrument):
    """
    Bond financial instrument.
    """
    issuer: Optional[List[Issuer]] = Field(None, description="The legal entity that is contractually responsible for the rights or obligations embedded in this instrument. ")
    industrySector: Optional[IndustrySector] = Field(None, description="Industry/sector classification of the bond issuer.")
    instrumentEsgProfile: Optional[ESGInstrumentProfile] = Field(None, description="ESG profile of the bond, allowing instrument-specific overlays.")
    creditRisk: Optional[CreditRisk] = Field(None, description="Credit risk profile of the bond instrument.")
    interestRate: Optional[InterestRate] = Field(None, description="Interest rate definition.")
    seniority: Optional[str] = Field(None, description="Seniority of the bond in the issuer's capital structure (default order of recovery on default / liquidation). Drives credit risk and recovery analytics independently of the issuer's overall creditworthiness. ")
    maturityDate: Optional[date] = Field(None, description="Bond maturity date.")
    issueDate: Optional[date] = Field(None, description="Issue date of the bond.")
    conversionPrice: Optional[Price] = Field(None, description="Conversion price if bond is convertible.")
    currencyOfDenomination: Optional[Currency] = Field(None, description="Currency in which the bond is denominated.")
    minimumDenomination: Optional[float] = Field(None, description="Minimum denomination allowed for trading.")
    minimumIncrement: Optional[float] = Field(None, description="Minimum tradable increment.")
    underlyingFinancialInstrument: Optional[FinancialInstrument] = Field(None, description="Underlying financial instrument for structured / convertible bonds.")

class MoneyMarket(FinancialInstrument):
    """
    Money market instrument (e.g., treasury bill, commercial paper).
    """
    creditRisk: Optional[CreditRisk] = Field(None, description="Credit risk profile of the money market instrument.")
    discountRate: Optional[Decimal] = Field(None, description="The rate used to determine the purchase price of money market instruments.")
    faceValue: Optional[CurrencyAmount] = Field(None, description="The amount paid to the holder at maturity.")
    issueDate: Optional[date] = Field(None, description="The date the instrument was created and sold.")
    maturityDate: Optional[date] = Field(None, description="The date the principal and interest are settled.")
    dayCountBasis: Optional[DayCountBasis] = Field(None, description="Standard calculation method for interest accrual (e.g., ACT/360).")

class Credit(FinancialInstrument):
    """
    Credit financial instrument.
    """
    issuer: Optional[List[Issuer]] = Field(None, description="The legal entity that is contractually responsible for the rights or obligations embedded in this instrument. ")
    creditRisk: Optional[CreditRisk] = Field(None, description="Credit risk profile of the credit instrument.")
    principalAmount: Optional[CurrencyAmount] = Field(None, description="Principal amount of the credit instrument.")
    currentBalance: Optional[CurrencyAmount] = Field(None, description="Current outstanding balance, including any capitalized interest.")
    interestRate: Optional[InterestRate] = Field(None, description="Interest rate applied to the credit instrument.")
    creditType: Optional[str] = Field(None, description="Category of credit (e.g., lombard loan, mortgage, fixed-term loan, overdraft, guarantee).")
    startDate: Optional[date] = Field(None, description="Date the loan was disbursed to the borrower.")
    maturityDate: Optional[date] = Field(None, description="Date the final payment is due and the contract ends.")
    repaymentType: Optional[str] = Field(None, description="Repayment structure for principal and interest.")
    repaymentSchedule: Optional[str] = Field(None, description="Schedule or rule defining repayment timing and installments.")
    amortizationSchedule: Optional[str] = Field(None, description="Details of the amortization plan or reference to an external schedule.")
    collateralIds: Optional[List[str]] = Field(None, description="Identifiers of assets backing the loan (e.g., portfolio or property identifiers).")
    currentLtv: Optional[float] = Field(None, description="Current loan-to-value ratio of the loan balance to collateral value.")
    marginCallThreshold: Optional[float] = Field(None, description="LTV percentage that triggers a margin call for additional collateral.")
    liquidationLevel: Optional[float] = Field(None, description="LTV percentage where collateral is liquidated to repay the loan.")
    accruedInterest: Optional[CurrencyAmount] = Field(None, description="Interest accrued but not yet paid by the borrower.")
    capitalizedInterestFlag: Optional[bool] = Field(None, description="Indicates whether unpaid interest is capitalized into the principal.")
    isOverdraft: Optional[bool] = Field(None, description="Indicates whether the raw_data represents an overdraft or negative cash balance.")
    limit: Optional[float] = Field(None, description="Maximum credit limit available.")
    underlyingFinancialInstrument: Optional[FinancialInstrument] = Field(None, description="Underlying financial instrument for structured credits.")

class Mortgage(FinancialInstrument):
    """
    Mortgage financial instrument.
    """
    notionalAmount: Optional[CurrencyAmount] = Field(None, description="Face value or original principal amount of the mortgage.")
    creditRisk: Optional[CreditRisk] = Field(None, description="Credit risk profile of the mortgage instrument.")
    interestRate: Optional[InterestRate] = Field(None, description="Percentage rate charged on the mortgage (fixed or floating).")
    maturityDate: Optional[date] = Field(None, description="Final date when the total principal and interest must be settled.")
    currency: Optional[Currency] = Field(None, description="ISO 4217 code for the mortgage payments.")
    creditSupport: Optional[CreditSupport] = Field(None, description="Collateral or security agreement linked to the property deed.")
    underlyingAsset: Optional[str] = Field(None, description="Legal description or identifier of the property acting as collateral.")
    paymentFrequency: Optional[str] = Field(None, description="Schedule of mortgage payments.")
    settlementType: Optional[str] = Field(None, description="Settlement method for mortgage payments.")
    initialMargin: Optional[CurrencyAmount] = Field(None, description="Down payment amount at mortgage inception.")
    amortizationType: Optional[str] = Field(None, description="Method of principal reduction over time.")
